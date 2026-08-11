import re
import os
import copy
import requests
import urllib.parse
from .base_tool import BaseTool
from .http_utils import request_with_retry
from .tool_registry import register_tool


# ---- openFDA `count=` aggregation paging ----
#
# openFDA answers a `count=` query with only the most frequent values and does
# NOT report how many distinct values exist -- its `meta` block carries just
# disclaimer/terms/license/last_updated, never a grand total. Measured live
# 2026-08 against
#   https://api.fda.gov/drug/event.json?search=...&count=patient.reaction.reactionmeddrapt.exact
# an unqualified count query returns exactly 100 rows, so 100 is the effective
# default page size for these aggregations.
COUNT_DEFAULT_LIMIT = 100

# Documented maximum for `limit`: "Currently, the largest allowed value for the
# `limit` parameter is 1000." -- https://open.fda.gov/apis/query-parameters/
COUNT_MAX_LIMIT = 1000

# Measured, undocumented: anonymous callers are capped one below the documented
# maximum. limit=1000 (and above) answers HTTP 403 {"code": "API_KEY_MISSING"}
# while limit=999 succeeds, reproduced across both count and plain search
# queries. Callers with FDA_API_KEY set may use the full documented maximum.
COUNT_MAX_LIMIT_ANONYMOUS = 999


def _is_error_payload(payload):
    """True when ``_search`` returned an error sentinel rather than count rows."""
    return (
        isinstance(payload, list)
        and len(payload) > 0
        and isinstance(payload[0], dict)
        and "error" in payload[0]
        and "term" not in payload[0]
    )


def _is_range(value):
    """True for a Lucene range such as "[20141001 TO 20141231]".

    These carry spaces yet must be sent unquoted; quoting turns the range into a
    literal term and the query matches nothing.
    """
    return bool(
        isinstance(value, str)
        and re.match(r"^\s*[\[\{].+\sTO\s.+[\]\}]\s*$", value, re.IGNORECASE)
    )


def _render_clause(fda_field_name, value):
    """Render a single ``field:value`` Lucene clause for an openFDA search.

    This is the ONE place that decides whether a mapped parameter value gets
    quoted. A multi-word term ("ACUTE KIDNEY INJURY") must be quoted, otherwise
    Lucene splits it and the trailing words become free-text clauses; a Lucene
    range ("[20141001 TO 20141231]") also contains spaces but must NOT be quoted,
    because quoting makes openFDA match it as a literal string and return
    nothing.

    The rule used to be spelled out separately in each builder's multi-field and
    single-field branches, and they drifted: the range exemption was added to the
    multi-field branches only, so `receivedate` -- which maps to a single field --
    kept being quoted and a date-bounded query such as
    ``FAERS_count_reactions_by_drug_event(receivedate="[20141001 TO 20141231]")``
    silently returned zero rows. Keep this logic here so the paths cannot drift
    again.
    """
    if isinstance(value, str) and " " in value and not _is_range(value):
        return f'{fda_field_name}:"{value}"'
    return f"{fda_field_name}:{value}"


def _render_field_group(fda_fields, value):
    """Render the clause for one parameter across every FDA field it maps to.

    Several fields for one parameter are OR-ed, and the group MUST be
    parenthesized: openFDA/Lucene binds AND tighter than OR, so an un-grouped
    "a:x OR b:x AND c:y OR d:y" parses as "a:x OR (b:x AND c:y) OR d:y" --
    wrong. That silently broke every filtered multi-field query, e.g. FAERS
    colistin + reaction "acute kidney injury" returned 0 (HTTP 404) even though
    the unfiltered count shows ACUTE KIDNEY INJURY = 151. Wrapping keeps
    "(a OR b) AND (c OR d)".
    """
    clauses = [_render_clause(name, value) for name in fda_fields]
    if len(clauses) == 1:
        return clauses[0]
    return "(" + "+OR+".join(clauses) + ")"


# ---- Helper: human readable -> openFDA code mapping ----
HUMAN_TO_FDA_MAP = {
    "fulfillexpeditecriteria": {"Yes": "1", "No": "2"},
    "patient.patientsex": {"Unknown": "0", "Male": "1", "Female": "2"},
    "patient.patientagegroup": {
        "Neonate": "1",
        "Infant": "2",
        "Child": "3",
        "Adolescent": "4",
        "Adult": "5",
        "Elderly": "6",
    },
    "patientonsetageunit": {
        "Decade": "800",
        "Year": "801",
        "Month": "802",
        "Week": "803",
        "Day": "804",
        "Hour": "805",
    },
    "patient.reaction.reactionoutcome": {
        "Recovered/resolved": "1",
        "Recovering/resolving": "2",
        "Not recovered/not resolved": "3",
        "Recovered/resolved with sequelae": "4",
        "Fatal": "5",
        "Unknown": "6",
    },
    "serious": {"Yes": "1", "No": "2"},
    "seriousnessdeath": {"Yes": "1"},
    "seriousnesshospitalization": {"Yes": "1"},
    "seriousnessdisabling": {"Yes": "1"},
    "seriousnesslifethreatening": {"Yes": "1"},
    "seriousnessother": {"Yes": "1"},
    "primarysource.qualification": {
        "Physician": "1",
        "Pharmacist": "2",
        "Other health professional": "3",
        "Lawyer": "4",
        "Consumer or non-health professional": "5",
    },
    "patient.drug.drugcharacterization": {
        "Suspect": "1",
        "Concomitant": "2",
        "Interacting": "3",
    },
    "patient.drug.drugadministrationroute": {
        "Oral": "048",
        "Intravenous": "042",
        "Intramuscular": "030",
        "Subcutaneous": "058",
        "Rectal": "054",
        "Topical": "061",
        "Respiratory (inhalation)": "055",
        "Ophthalmic": "047",
        "Unknown": "065",
    },
}


# ---- Base Tool Class ----
@register_tool("FDADrugAdverseEventTool")
class FDADrugAdverseEventTool(BaseTool):
    def __init__(
        self,
        tool_config,
        endpoint_url="https://api.fda.gov/drug/event.json",
        api_key=None,
    ):
        super().__init__(tool_config)
        self.endpoint_url = endpoint_url
        self.api_key = api_key or os.getenv("FDA_API_KEY")
        self.search_fields = tool_config.get("fields", {}).get("search_fields", {})
        self.return_fields = tool_config.get("fields", {}).get("return_fields", [])
        self.count_field = tool_config.get("count_field") or (
            self.return_fields[0] if self.return_fields else None
        )
        self.return_fields_mapping = tool_config.get("fields", {}).get(
            "return_fields_mapping", {}
        )

        if not self.count_field:
            raise ValueError(
                "Either 'count_field' or 'return_fields' must be defined in tool_config."
            )

        # Opt-in per tool. An openFDA `count=` facet is computed ONLY over
        # records that populate the counted field, so the rows can sum to far
        # less than the number of matching reports and a reader who divides one
        # row by the row total gets a badly wrong rate. Disclosing the true
        # denominator costs an extra request, and it is only meaningful when the
        # counted field holds at most one value per report: a report carries a
        # single `seriousnessdeath` flag, but many reaction terms, so a reaction
        # facet legitimately sums ABOVE the report total and a coverage fraction
        # there would be nonsense. Tools whose count_field is report-level set
        # "disclose_denominator": true in their JSON config. Only this class's
        # run() honours the flag; FDACountAdditiveReactionsTool builds its query
        # differently and would need its own denominator probe, so setting the
        # flag on one of its configs is currently a no-op.
        self.disclose_denominator = bool(tool_config.get("disclose_denominator", False))
        # Optional per-tool sentence about what the counted field actually means,
        # prepended to `coverage_note`. Needed where the field name invites a
        # clinical misreading -- see the FAERS_count_death_related_by_drug config.
        self.count_field_note = tool_config.get("count_field_note", "")

        # Store allowed enum values
        self.parameter_enums = {}
        if "parameter" in tool_config and "properties" in tool_config["parameter"]:
            for param_name, param_def in tool_config["parameter"]["properties"].items():
                if "enum" in param_def:
                    self.parameter_enums[param_name] = param_def["enum"]

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)

        # Validate enum parameters
        validation_error = self.validate_enum_arguments(arguments)
        if validation_error:
            return {"status": "error", "error": validation_error}

        limit_error, limit = self._resolve_count_limit(arguments)
        if limit_error:
            return {"status": "error", "error": limit_error}

        # Store reactionmeddraverse for filtering results
        reaction_filter = arguments.get("reactionmeddraverse")

        response = self._search(arguments, limit=self._fetch_limit(limit))
        if _is_error_payload(response):
            return response
        envelope = self._build_count_envelope(
            response, limit, reaction_filter=reaction_filter
        )
        if self.disclose_denominator:
            self._add_coverage_disclosure(envelope, arguments, response)
        return envelope

    # ---- count paging / truncation disclosure ----

    def _limit_ceiling(self):
        """Highest `limit` this caller may send to openFDA."""
        return COUNT_MAX_LIMIT if self.api_key else COUNT_MAX_LIMIT_ANONYMOUS

    def _resolve_count_limit(self, arguments):
        """Pop and validate `limit`, returning ``(error_message, limit)``."""
        limit = arguments.pop("limit", COUNT_DEFAULT_LIMIT)
        if limit is None:
            limit = COUNT_DEFAULT_LIMIT
        if isinstance(limit, bool) or not isinstance(limit, int):
            message = (
                f"Invalid value '{limit}' for 'limit'. Expected an integer between 1 "
                f"and {COUNT_MAX_LIMIT}."
            )
            return message, None
        if limit < 1 or limit > COUNT_MAX_LIMIT:
            message = (
                f"'limit' must be between 1 and {COUNT_MAX_LIMIT} "
                f"(openFDA's documented maximum); got {limit}."
            )
            return message, None
        if limit > self._limit_ceiling():
            message = (
                f"'limit' above {COUNT_MAX_LIMIT_ANONYMOUS} requires an openFDA API "
                "key: set the FDA_API_KEY environment variable, or lower 'limit' to "
                f"{COUNT_MAX_LIMIT_ANONYMOUS} or below."
            )
            return message, None
        return None, limit

    def _fetch_limit(self, limit):
        """Ask openFDA for one extra row so truncation can be reported exactly.

        openFDA never states how many distinct values a `count=` aggregation has,
        so the only way to know whether the caller's page is the whole story is
        to request one row past it and see whether it comes back.
        """
        return min(limit + 1, self._limit_ceiling())

    def _build_count_envelope(self, response, limit, reaction_filter=None):
        """Return count rows alongside a top-level truncation disclosure."""
        if not isinstance(response, list):
            response = []

        fetch_limit = self._fetch_limit(limit)
        probed = fetch_limit > limit
        if probed:
            # The probe row came back, so more terms definitely exist.
            truncated = len(response) > limit
        else:
            # Already at the ceiling: a full page is all we can observe, so the
            # honest answer is "possibly incomplete", not "complete".
            truncated = len(response) >= limit

        rows = self._post_process(response[:limit], reaction_filter=reaction_filter)

        envelope = {
            "results": rows,
            "result_count": len(rows),
            "limit": limit,
            "truncated": truncated,
        }
        if truncated:
            certainty = (
                "more terms exist beyond that limit"
                if probed
                else "openFDA filled the page exactly, so more terms may exist beyond it"
            )
            # When a term filter is applied client-side, 'results' is a subset of
            # the ranked list; say so, so the flag is not read as "your one row
            # is incomplete".
            scope = (
                " 'results' was then narrowed to the requested term, so the "
                "truncation applies to the underlying ranking rather than to the "
                "rows shown."
                if reaction_filter
                else ""
            )
            envelope["truncation_note"] = (
                f"openFDA returned only the {min(len(response), limit)} most-reported "
                f"terms for this query (limit={limit}), ranked by descending report "
                f"count; {certainty}. openFDA's count endpoint does not report how "
                "many distinct terms there are in total, so the size of the remainder "
                f"is unknown. Pass a larger 'limit' (maximum {COUNT_MAX_LIMIT}) to "
                "retrieve more. A term missing from this list is NOT evidence that it "
                f"was never reported -- query the term directly to check.{scope}"
            )
        return envelope

    # ---- openFDA `count=` facet coverage disclosure ----

    def _fetch_query_total(self, arguments):
        """Reports matching this tool's own search, or ``None`` if unavailable.

        A `count=` response carries no grand total -- openFDA reports the size of
        a search only in `meta.results.total` of a plain (non-count) request, so
        the denominator needs a second call. It is built from the SAME
        ``_build_search_query`` as the facet, otherwise the two figures would not
        be comparable.

        `limit=0` asks for the size without any report bodies: it returns the
        same `meta.results.total` in ~0.5 KB where `limit=1` ships a whole FAERS
        report (~120 KB, mostly `openfda` arrays) only to discard it. A search
        with no matches still answers HTTP 404 either way.
        """
        query_error, search_query = self._build_search_query(arguments)
        if query_error:
            return None
        search_encoded = urllib.parse.quote(search_query, safe='+:"')
        key = f"api_key={self.api_key}&" if self.api_key else ""
        url = f"{self.endpoint_url}?{key}search={search_encoded}&limit=0"
        try:
            # request_with_retry backs off on 429, which this probe makes more
            # likely by doubling the tool's request rate -- one retry is cheaper
            # than degrading to a null denominator. Every budget here is kept
            # well under the facet's 30s: this request fails soft by design, so
            # it must not dominate the caller's worst case. Note the Retry-After
            # sleep happens OUTSIDE the per-request timeout, hence capping it
            # too -- worst case is 10 + 5 + 10 = 25s rather than the default
            # helper's 90s.
            response = request_with_retry(
                requests,
                "GET",
                url,
                timeout=10,
                max_attempts=2,
                max_retry_after_seconds=5,
            )
            # openFDA answers a search with no matches with HTTP 404, which here
            # means a genuine zero rather than a failure to measure.
            if response.status_code == 404:
                return 0
            response.raise_for_status()
            total = response.json().get("meta", {}).get("results", {}).get("total")
            return total if isinstance(total, int) else None
        except (requests.exceptions.RequestException, ValueError):
            return None

    def _add_coverage_disclosure(self, envelope, arguments, response):
        """Add the true denominator next to the facet, without changing it.

        openFDA computes a count facet solely over records that populate the
        counted field. Reports where the field is absent are dropped from the
        facet rather than bucketed as unknown, so the rows do NOT sum to the
        number of matching reports -- for `seriousnessdeath` roughly half of
        FAERS reports carry no value at all. Dividing one row by the row sum
        therefore overstates a fatality share several-fold, which is exactly the
        number that ends up on a clinical slide. Report both figures under
        self-describing names and say plainly that they do not support a rate.

        Purely additive: `results`, `result_count`, `limit` and `truncated` are
        untouched, and a failed denominator request leaves a null rather than
        turning a working call into an error.
        """
        # Sum the RAW facet rows rather than envelope["results"]: a client-side
        # reaction_filter subsets 'results' to one term, and the facet coverage
        # being described here is a property of the whole facet, not of the rows
        # that survived filtering.
        subset = sum(
            row["count"]
            for row in response[: envelope["limit"]]
            if isinstance(row, dict) and isinstance(row.get("count"), int)
        )
        query_total = self._fetch_query_total(arguments)

        envelope["stratified_report_count"] = subset
        envelope["total_reports_matching_query"] = query_total

        if query_total is None:
            coverage_note = (
                "The total number of reports matching this query could not be "
                "retrieved (the extra openFDA request failed, commonly HTTP 429 "
                "rate limiting on the anonymous tier), so "
                "total_reports_matching_query is null. "
                f"stratified_report_count ({subset:,}) counts only reports where "
                f"{self.count_field} is recorded and is therefore a LOWER BOUND "
                "on the number of matching reports -- do not read it as the "
                "total, and do not divide a row by it to obtain a rate. Retry "
                "for the total, or set the FDA_API_KEY environment variable to "
                "raise the rate limit "
                "(https://open.fda.gov/apis/authentication/)."
            )
        else:
            coverage = (subset / query_total * 100) if query_total else 0.0
            coverage_note = (
                f"total_reports_matching_query ({query_total:,}) is every report "
                f"matching this query; stratified_report_count ({subset:,}, "
                f"{coverage:.1f}% of them) is the subset where {self.count_field} "
                "is recorded, and only that subset is counted in 'results'. "
                "openFDA computes a count facet solely over records that populate "
                "the counted field, so reports missing it are absent from the "
                "rows entirely rather than bucketed as unknown. These counts "
                "therefore do NOT support a case-fatality rate: neither "
                "denominator is the population at risk."
            )
        if self.count_field_note:
            coverage_note = f"{self.count_field_note} {coverage_note}"
        envelope["coverage_note"] = coverage_note

    def validate_enum_arguments(self, arguments):
        """Validate that enum-based arguments match the allowed values"""
        for param_name, value in arguments.items():
            if param_name in self.parameter_enums and value is not None:
                allowed_values = self.parameter_enums[param_name]
                if value not in allowed_values:
                    return f"Invalid value '{value}' for parameter '{param_name}'. Allowed values are: {', '.join(allowed_values)}"
        return None

    def _post_process(self, response, reaction_filter=None):
        if not response or not isinstance(response, list):
            return []

        mapped_results = []
        for item in response:
            try:
                # Pass through error sentinels from _search untouched so an
                # upstream API failure surfaces instead of being masked as a
                # bogus {"term": None, "count": 0} row.
                if isinstance(item, dict) and "error" in item and "term" not in item:
                    mapped_results.append(item)
                    continue

                term = item.get("term")
                count = item.get("count", 0)

                # If reaction_filter is specified, only include matching reactions
                if reaction_filter is not None:
                    # Case-insensitive comparison
                    if term and term.upper() != reaction_filter.upper():
                        continue

                # Apply mapping if available. Fall back to the raw code as a
                # string (not the original int/etc) so an FDA code absent
                # from our mapping (e.g. an undocumented drugcharacterization
                # value) still satisfies the documented "term is a string"
                # contract instead of leaking a raw int through.
                if self.return_fields_mapping:
                    mapped_term = self.return_fields_mapping.get(
                        self.count_field, {}
                    ).get(str(term), str(term))
                    mapped_results.append({"term": mapped_term, "count": count})
                else:
                    mapped_results.append({"term": term, "count": count})
            except Exception:
                # Keep the original term in case of an exception
                if reaction_filter is None or (
                    isinstance(item, dict)
                    and item.get("term", "").upper() == reaction_filter.upper()
                ):
                    mapped_results.append(item)

        return mapped_results

    def _build_search_query(self, arguments):
        """Build the Lucene `search=` expression, returning ``(error, query)``.

        Kept separate from the request so the same query can also be reused for
        the denominator probe in ``_fetch_query_total``.
        """
        search_parts = []
        for param_name, value in arguments.items():
            # Only forward parameters defined in the search-field map; an
            # unrecognized argument (e.g. a stray 'limit') must NOT become a
            # bogus FDA filter like 'limit:2', which matches nothing and yields
            # a silent empty result.
            fda_fields = self.search_fields.get(param_name)
            if not fda_fields:
                continue
            # Use the first field name for value mapping
            fda_field = fda_fields[0]

            # Apply value mapping using FDA field name
            # (for proper enum mapping)
            mapping_error, mapped_value = self._map_value(fda_field, value)
            if mapping_error:
                return mapping_error, None
            if mapped_value is None:
                continue  # Skip this field if instructed

            # Build search parts using FDA field name(s). Multiple fields for the
            # same parameter are OR-ed inside a parenthesized group.
            search_parts.append(_render_field_group(fda_fields, mapped_value))

        # Final search query - join different parameters with AND
        return None, "+AND+".join(search_parts)

    def _search(self, arguments, limit=None):
        query_error, search_query = self._build_search_query(arguments)
        if query_error:
            return [{"error": query_error}]
        search_encoded = urllib.parse.quote(search_query, safe='+:"')

        # Build URL. `limit` is appended after `count` so it is never mistaken
        # for part of the Lucene search clause.
        if self.api_key:
            url = f"{self.endpoint_url}?api_key={self.api_key}&search={search_encoded}&count={self.count_field}"
        else:
            url = (
                f"{self.endpoint_url}?search={search_encoded}&count={self.count_field}"
            )
        if limit is not None:
            url = f"{url}&limit={limit}"

        # API request (30s timeout so a hung connection cannot block the caller)
        try:
            response = requests.get(url, timeout=30)
            # Handle 404 as "no matches found" - return empty list instead of error
            if response.status_code == 404:
                try:
                    error_data = response.json()
                    if "error" in error_data and "No matches found" in str(
                        error_data.get("error", {})
                    ):
                        return []  # Return empty list for no matches
                except (ValueError, KeyError):
                    pass
            response.raise_for_status()
            response = response.json()
            if "results" in response:
                response = response["results"]
            return response
        except requests.exceptions.RequestException as e:
            return [{"error": f"API request failed: {str(e)}"}]

    def _map_value(self, param_name, value):
        # Special handling for seriousness fields: if value is "No", skip this field
        seriousness_fields = {
            "seriousnessdeath",
            "seriousnesshospitalization",
            "seriousnessdisabling",
            "seriousnesslifethreatening",
            "seriousnessother",
        }
        if param_name in seriousness_fields:
            if value == "No":
                return None, None  # Signal to skip this field
            # Feature-66B-005: also accept native openFDA integer 1 or string "1" as "Yes"
            if value in ("Yes", 1, "1"):
                return None, "1"
            # If not Yes/No/1, error
            return (
                f"Invalid value '{value}' for '{param_name}'. Allowed values: ['Yes'] (omit to include all).",
                None,
            )

        if param_name in HUMAN_TO_FDA_MAP:
            value_map = HUMAN_TO_FDA_MAP[param_name]
            if value not in value_map:
                print("No mapping found for value:", value, "skipping")
                allowed_values = list(value_map.keys())
                return (
                    f"Invalid value '{value}' for '{param_name}'. Allowed values: {allowed_values}",
                    None,
                )
            return None, value_map[value]
        return None, value


@register_tool("FDACountAdditiveReactionsTool")
class FDACountAdditiveReactionsTool(FDADrugAdverseEventTool):
    """
    Leverage openFDA API to count adverse reaction events across multiple drugs in one request.
    """

    def __init__(
        self,
        tool_config,
        endpoint_url="https://api.fda.gov/drug/event.json",
        api_key=None,
    ):
        super().__init__(tool_config)

    def run(self, arguments):
        # Make a copy to avoid modifying the original
        arguments = copy.deepcopy(arguments)

        # Validate medicinalproducts list first
        drugs = arguments.pop("medicinalproducts", [])
        if not drugs:
            return {"status": "error", "error": "`medicinalproducts` list is required."}
        if not isinstance(drugs, list):
            return {
                "status": "error",
                "error": "`medicinalproducts` must be a list of drug names.",
            }

        # Validate the remaining enum parameters
        validation_error = self.validate_enum_arguments(arguments)
        if validation_error:
            return {"status": "error", "error": validation_error}

        limit_error, limit = self._resolve_count_limit(arguments)
        if limit_error:
            return {"status": "error", "error": limit_error}

        # Build OR clause for multiple drugs. The drug name goes through the
        # shared clause renderer for the same reason every other value does: a
        # multi-word name needs Lucene quotes, and the percent-encoding is done
        # ONCE, below, on the finished query.
        #
        # Percent-encoding the name here as well used to double-encode it. The
        # space in "SODIUM CHLORIDE" became %2520; openFDA decoded that once to
        # the literal term "SODIUM%20CHLORIDE", whose analyzer split it and left
        # the field bound to the first token alone. The query silently widened
        # to every product whose name merely contains "SODIUM" -- and because it
        # returned MORE data rather than none, nothing looked broken. Verified
        # live against the API: medicinalproduct:"SODIUM CHLORIDE" counts
        # 74,079 serious + 16,715 non-serious = 90,794, while the double-encoded
        # form returns 605,620 + 173,560 = 779,180, exactly equal to the count
        # for the bare term "SODIUM" -- an 8.6x over-count.
        or_clause = "+OR+".join(
            _render_clause("patient.drug.medicinalproduct", d) for d in drugs
        )

        # Combine additional filters
        filters = []
        for k, v in arguments.items():
            # Get FDA field name(s) from the search-field map; skip unrecognized
            # filters rather than forwarding them as bogus FDA constraints.
            fda_fields = self.search_fields.get(k)
            if not fda_fields:
                continue
            # Use the first field name for value mapping
            fda_field = fda_fields[0]

            # Map value using FDA field name (for proper enum mapping)
            mapping_error, mapped = self._map_value(fda_field, v)
            if mapping_error:
                return {"status": "error", "error": mapping_error}
            if mapped is None:
                continue  # Skip this field if instructed

            # Use FDA field name(s) in the query via the shared renderer, so both
            # the quoting rule (a Lucene range stays unquoted) and the grouping
            # rule (several fields for one parameter are OR-ed inside parens)
            # have exactly one home. Every config for this tool type maps each
            # parameter to a single field today, so this is currently a plain
            # clause -- routing it through the helper anyway keeps a future
            # multi-field config from silently AND-ing what should be OR-ed.
            filters.append(_render_field_group(fda_fields, mapped))

        filter_str = "+AND+".join(filters) if filters else ""
        search_query = f"({or_clause})" + (f"+AND+{filter_str}" if filter_str else "")
        # URL encode the search query, preserving +, :, and " as safe chars
        search_encoded = urllib.parse.quote(search_query, safe='+:"')

        # Call API. `limit` is appended after `count` so it is never mistaken
        # for part of the Lucene search clause.
        if self.api_key:
            url = (
                f"{self.endpoint_url}?api_key={self.api_key}"
                f"&search={search_encoded}&count={self.count_field}"
            )
        else:
            url = (
                f"{self.endpoint_url}?search={search_encoded}&count={self.count_field}"
            )
        url = f"{url}&limit={self._fetch_limit(limit)}"

        try:
            resp = requests.get(url)
            # Handle 404 as "no matches found" - return an empty (but explicitly
            # non-truncated) envelope instead of an error.
            if resp.status_code == 404:
                try:
                    error_data = resp.json()
                    if "error" in error_data and "No matches found" in str(
                        error_data.get("error", {})
                    ):
                        return self._build_count_envelope([], limit)
                except (ValueError, KeyError):
                    pass
            resp.raise_for_status()
            results = resp.json().get("results", [])
            return self._build_count_envelope(results, limit)
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"API request failed: {str(e)}"}


@register_tool("FDADrugAdverseEventDetailTool")
class FDADrugAdverseEventDetailTool(BaseTool):
    """
    Tool for retrieving detailed adverse event reports from FAERS.
    Uses limit/skip parameters instead of count aggregation.
    """

    def __init__(
        self,
        tool_config,
        endpoint_url="https://api.fda.gov/drug/event.json",
        api_key=None,
    ):
        super().__init__(tool_config)
        self.tool_config = tool_config
        self.endpoint_url = endpoint_url
        self.api_key = api_key or os.getenv("FDA_API_KEY")
        self.search_fields = tool_config.get("fields", {}).get("search_fields", {})
        self.return_fields = tool_config.get("fields", {}).get("return_fields", [])

        # Store allowed enum values
        self.parameter_enums = {}
        if "parameter" in tool_config and "properties" in tool_config["parameter"]:
            for param_name, param_def in tool_config["parameter"]["properties"].items():
                if "enum" in param_def:
                    self.parameter_enums[param_name] = param_def["enum"]

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)

        # Validate enum parameters
        validation_error = self.validate_enum_arguments(arguments)
        if validation_error:
            return [{"error": validation_error}]

        response = self._search(arguments)
        return response

    def validate_enum_arguments(self, arguments):
        """Validate that enum-based arguments match the allowed values"""
        for param_name, value in arguments.items():
            if param_name in self.parameter_enums and value is not None:
                allowed_values = self.parameter_enums[param_name]
                if value not in allowed_values:
                    return f"Invalid value '{value}' for parameter '{param_name}'. Allowed values are: {', '.join(allowed_values)}"
        return None

    def _search(self, arguments):
        # Extract limit and skip from arguments
        limit = arguments.pop("limit", 10)
        skip = arguments.pop("skip", 0)

        # Validate limit
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            return [{"error": "limit must be an integer between 1 and 100"}]
        if not isinstance(skip, int) or skip < 0:
            return [{"error": "skip must be a non-negative integer"}]

        # Build search query
        search_parts = []
        for param_name, value in arguments.items():
            # Only forward parameters defined in the search-field map; an
            # unrecognized argument (e.g. a stray 'limit') must NOT become a
            # bogus FDA filter like 'limit:2', which matches nothing and yields
            # a silent empty result.
            fda_fields = self.search_fields.get(param_name)
            if not fda_fields:
                continue
            # Use the first field name for value mapping
            fda_field = fda_fields[0]

            # Apply value mapping using FDA field name
            # (for proper enum mapping)
            mapping_error, mapped_value = self._map_value(fda_field, value)
            if mapping_error:
                return [{"error": mapping_error}]
            if mapped_value is None:
                continue  # Skip this field if instructed

            # Build search parts using FDA field name(s). Multiple fields for the
            # same parameter are OR-ed inside a parenthesized group.
            search_parts.append(_render_field_group(fda_fields, mapped_value))

        # Final search query - join different parameters with AND
        search_query = "+AND+".join(search_parts)
        search_encoded = urllib.parse.quote(search_query, safe='+:"')

        # Build URL with limit and skip (not count)
        if self.api_key:
            url = (
                f"{self.endpoint_url}?api_key={self.api_key}"
                f"&search={search_encoded}&limit={limit}&skip={skip}"
            )
        else:
            url = (
                f"{self.endpoint_url}?search={search_encoded}&limit={limit}&skip={skip}"
            )

        # API request
        try:
            response = requests.get(url)
            # Handle 404 as "no matches found" - return empty list instead of error
            if response.status_code == 404:
                try:
                    error_data = response.json()
                    if "error" in error_data and "No matches found" in str(
                        error_data.get("error", {})
                    ):
                        return []  # Return empty list for no matches
                except (ValueError, KeyError):
                    pass
            response.raise_for_status()
            response_data = response.json()
            results = response_data.get("results", [])

            # If return_fields is specified, filter the results
            if self.return_fields:
                filtered_results = []
                for result in results:
                    filtered_result = {}
                    for field in self.return_fields:
                        # Handle nested fields (e.g., "patient.reaction.reactionmeddrapt")
                        field_parts = field.split(".")
                        value = result
                        for part in field_parts:
                            if isinstance(value, dict):
                                value = value.get(part)
                            elif isinstance(value, list) and part.isdigit():
                                value = (
                                    value[int(part)] if int(part) < len(value) else None
                                )
                            else:
                                value = None
                                break
                        if value is not None:
                            filtered_result[field] = value
                    if filtered_result:
                        filtered_results.append(filtered_result)
                return filtered_results

            # Extract essential fields if configured
            extract_essential = self.tool_config.get("fields", {}).get(
                "extract_essential", False
            )
            if extract_essential:
                results = [self._extract_essential_fields(r) for r in results]

            return results
        except requests.exceptions.RequestException as e:
            return [{"error": f"API request failed: {str(e)}"}]

    def _extract_essential_fields(self, report):
        """
        Extract only essential fields from a FAERS report.
        Removes verbose metadata like openfda to keep output concise.
        Can be customized via tool_config['fields']['essential_fields'].
        """
        # Get custom essential fields from config, or use default
        essential_fields_config = self.tool_config.get("fields", {}).get(
            "essential_fields", None
        )

        if essential_fields_config:
            # Use custom field extraction logic from config
            return self._extract_custom_fields(report, essential_fields_config)

        # Default essential fields extraction
        essential = {
            # Report identification
            "safetyreportid": report.get("safetyreportid"),
            "safetyreportversion": report.get("safetyreportversion"),
            # Seriousness indicators
            "serious": report.get("serious"),
            "seriousnessdeath": report.get("seriousnessdeath"),
            "seriousnesshospitalization": report.get("seriousnesshospitalization"),
            "seriousnesslifethreatening": report.get("seriousnesslifethreatening"),
            "seriousnessdisabling": report.get("seriousnessdisabling"),
            # Location
            "occurcountry": report.get("occurcountry"),
            "primarysourcecountry": report.get("primarysourcecountry"),
            # Dates
            "transmissiondate": report.get("transmissiondate"),
            "receivedate": report.get("receivedate"),
        }

        # Patient information (essential fields only)
        patient = report.get("patient", {})
        if patient:
            essential_patient = {
                "patientsex": patient.get("patientsex"),
                "patientagegroup": patient.get("patientagegroup"),
                "patientonsetage": patient.get("patientonsetage"),
                "patientonsetageunit": patient.get("patientonsetageunit"),
                "patientweight": patient.get("patientweight"),
            }

            # Drugs (essential fields only, no openfda metadata)
            drugs = patient.get("drug", [])
            if drugs:
                essential_drugs = []
                for drug in drugs:
                    essential_drug = {
                        "medicinalproduct": drug.get("medicinalproduct"),
                        "drugindication": drug.get("drugindication"),
                        "drugadministrationroute": drug.get("drugadministrationroute"),
                        "drugdosagetext": drug.get("drugdosagetext"),
                        "drugdosageform": drug.get("drugdosageform"),
                        "drugstartdate": drug.get("drugstartdate"),
                        "actiondrug": drug.get("actiondrug"),
                    }
                    # Only include non-empty fields
                    essential_drug = {
                        k: v for k, v in essential_drug.items() if v is not None
                    }
                    if essential_drug:
                        essential_drugs.append(essential_drug)
                if essential_drugs:
                    essential_patient["drug"] = essential_drugs

            # Reactions (all fields are essential)
            reactions = patient.get("reaction", [])
            if reactions:
                essential_reactions = []
                for reaction in reactions:
                    essential_reaction = {
                        "reactionmeddrapt": reaction.get("reactionmeddrapt"),
                        "reactionmeddraversionpt": reaction.get(
                            "reactionmeddraversionpt"
                        ),
                        "reactionoutcome": reaction.get("reactionoutcome"),
                    }
                    # Only include non-empty fields
                    essential_reaction = {
                        k: v for k, v in essential_reaction.items() if v is not None
                    }
                    if essential_reaction:
                        essential_reactions.append(essential_reaction)
                if essential_reactions:
                    essential_patient["reaction"] = essential_reactions

            # Summary if available
            if "summary" in patient:
                essential_patient["summary"] = patient["summary"]

            essential["patient"] = essential_patient

        # Remove None values
        essential = {k: v for k, v in essential.items() if v is not None}
        return essential

    def _extract_custom_fields(self, report, field_config):
        """
        Extract fields based on custom configuration.
        field_config can be a list of field paths or a dict with inclusion rules.
        """
        if isinstance(field_config, list):
            # Simple list of field paths to include
            result = {}
            for field_path in field_config:
                value = self._get_nested_value(report, field_path)
                if value is not None:
                    self._set_nested_value(result, field_path, value)
            return result
        else:
            # Use default extraction
            return self._extract_essential_fields(report)

    def _get_nested_value(self, obj, path):
        """Get value from nested dict using dot notation path"""
        parts = path.split(".")
        value = obj
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list) and part.isdigit():
                value = value[int(part)] if int(part) < len(value) else None
            else:
                return None
            if value is None:
                return None
        return value

    def _set_nested_value(self, obj, path, value):
        """Set value in nested dict using dot notation path"""
        parts = path.split(".")
        current = obj
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    def _map_value(self, param_name, value):
        # Special handling for seriousness fields: if value is "No", skip this field
        seriousness_fields = {
            "seriousnessdeath",
            "seriousnesshospitalization",
            "seriousnessdisabling",
            "seriousnesslifethreatening",
            "seriousnessother",
        }
        if param_name in seriousness_fields:
            if value == "No":
                return None, None  # Signal to skip this field
            # Feature-66B-005: also accept native openFDA integer 1 or string "1" as "Yes"
            if value in ("Yes", 1, "1"):
                return None, "1"
            # If not Yes/No/1, error
            return (
                f"Invalid value '{value}' for '{param_name}'. Allowed values: ['Yes'] (omit to include all).",
                None,
            )

        if param_name in HUMAN_TO_FDA_MAP:
            value_map = HUMAN_TO_FDA_MAP[param_name]
            if value not in value_map:
                print("No mapping found for value:", value, "skipping")
                allowed_values = list(value_map.keys())
                return (
                    f"Invalid value '{value}' for '{param_name}'. Allowed values: {allowed_values}",
                    None,
                )
            return None, value_map[value]
        return None, value


@register_tool("FDADrugInteractionDetailTool")
class FDADrugInteractionDetailTool(BaseTool):
    """
    Tool for retrieving detailed adverse event reports involving multiple drugs (drug interactions).
    Uses limit/skip parameters instead of count aggregation.
    """

    def __init__(
        self,
        tool_config,
        endpoint_url="https://api.fda.gov/drug/event.json",
        api_key=None,
    ):
        super().__init__(tool_config)
        self.tool_config = tool_config
        self.endpoint_url = endpoint_url
        self.api_key = api_key or os.getenv("FDA_API_KEY")
        self.search_fields = tool_config.get("fields", {}).get("search_fields", {})
        self.return_fields = tool_config.get("fields", {}).get("return_fields", [])

        # Store allowed enum values
        self.parameter_enums = {}
        if "parameter" in tool_config and "properties" in tool_config["parameter"]:
            for param_name, param_def in tool_config["parameter"]["properties"].items():
                if "enum" in param_def:
                    self.parameter_enums[param_name] = param_def["enum"]

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)

        # Validate enum parameters
        validation_error = self.validate_enum_arguments(arguments)
        if validation_error:
            return [{"error": validation_error}]

        response = self._search(arguments)
        return response

    def validate_enum_arguments(self, arguments):
        """Validate that enum-based arguments match the allowed values"""
        for param_name, value in arguments.items():
            if param_name in self.parameter_enums and value is not None:
                allowed_values = self.parameter_enums[param_name]
                if value not in allowed_values:
                    return f"Invalid value '{value}' for parameter '{param_name}'. Allowed values are: {', '.join(allowed_values)}"
        return None

    def _search(self, arguments):
        # Extract limit and skip from arguments
        limit = arguments.pop("limit", 10)
        skip = arguments.pop("skip", 0)

        # Validate limit
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            return [{"error": "limit must be an integer between 1 and 100"}]
        if not isinstance(skip, int) or skip < 0:
            return [{"error": "skip must be a non-negative integer"}]

        # Extract medicinalproducts list
        drugs = arguments.pop("medicinalproducts", [])
        if not drugs:
            return [{"error": "medicinalproducts list is required"}]
        if not isinstance(drugs, list) or len(drugs) < 2:
            return [
                {"error": "medicinalproducts must be a list of at least 2 drug names"}
            ]

        # Build AND clause for multiple drugs (all must be present). Routed
        # through the shared clause renderer so a multi-word name gets Lucene
        # quotes and is percent-encoded exactly once, on the finished query
        # below -- encoding it here too widened each clause to the name's first
        # token (see the matching note in FDACountAdditiveReactionsTool.run).
        drug_parts = [
            _render_clause("patient.drug.medicinalproduct", drug) for drug in drugs
        ]

        # Build additional filters
        filter_parts = []
        for param_name, value in arguments.items():
            # Skip unrecognized arguments rather than forwarding them as bogus
            # FDA filters (which silently match nothing).
            fda_fields = self.search_fields.get(param_name)
            if not fda_fields:
                continue
            # Use the first field name for value mapping
            fda_field = fda_fields[0]

            # Apply value mapping using FDA field name
            mapping_error, mapped_value = self._map_value(fda_field, value)
            if mapping_error:
                return [{"error": mapping_error}]
            if mapped_value is None:
                continue  # Skip this field if instructed

            # Build filter parts through the shared renderer, so the quoting rule
            # (a Lucene range stays unquoted) and the grouping rule (several
            # fields for one parameter are OR-ed inside parens) have one home.
            filter_parts.append(_render_field_group(fda_fields, mapped_value))

        # Combine drug parts (AND) with additional filters (AND)
        all_parts = drug_parts + filter_parts
        search_query = "+AND+".join(all_parts)
        search_encoded = urllib.parse.quote(search_query, safe='+:"')

        # Build URL with limit and skip
        if self.api_key:
            url = (
                f"{self.endpoint_url}?api_key={self.api_key}"
                f"&search={search_encoded}&limit={limit}&skip={skip}"
            )
        else:
            url = (
                f"{self.endpoint_url}?search={search_encoded}&limit={limit}&skip={skip}"
            )

        # API request
        try:
            response = requests.get(url)
            # Handle 404 as "no matches found" - return empty list instead of error
            if response.status_code == 404:
                try:
                    error_data = response.json()
                    if "error" in error_data and "No matches found" in str(
                        error_data.get("error", {})
                    ):
                        return []  # Return empty list for no matches
                except (ValueError, KeyError):
                    pass
            response.raise_for_status()
            response_data = response.json()
            results = response_data.get("results", [])

            # If return_fields is specified, filter the results
            if self.return_fields:
                filtered_results = []
                for result in results:
                    filtered_result = {}
                    for field in self.return_fields:
                        # Handle nested fields (e.g., "patient.reaction.reactionmeddrapt")
                        field_parts = field.split(".")
                        value = result
                        for part in field_parts:
                            if isinstance(value, dict):
                                value = value.get(part)
                            elif isinstance(value, list) and part.isdigit():
                                value = (
                                    value[int(part)] if int(part) < len(value) else None
                                )
                            else:
                                value = None
                                break
                        if value is not None:
                            filtered_result[field] = value
                    if filtered_result:
                        filtered_results.append(filtered_result)
                return filtered_results

            # Extract essential fields if configured
            extract_essential = self.tool_config.get("fields", {}).get(
                "extract_essential", False
            )
            if extract_essential:
                results = [self._extract_essential_fields(r) for r in results]

            return results
        except requests.exceptions.RequestException as e:
            return [{"error": f"API request failed: {str(e)}"}]

    def _extract_essential_fields(self, report):
        """
        Extract only essential fields from a FAERS report.
        Removes verbose metadata like openfda to keep output concise.
        Can be customized via tool_config['fields']['essential_fields'].
        """
        # Get custom essential fields from config, or use default
        essential_fields_config = self.tool_config.get("fields", {}).get(
            "essential_fields", None
        )

        if essential_fields_config:
            # Use custom field extraction logic from config
            return self._extract_custom_fields(report, essential_fields_config)

        # Default essential fields extraction
        essential = {
            # Report identification
            "safetyreportid": report.get("safetyreportid"),
            "safetyreportversion": report.get("safetyreportversion"),
            # Seriousness indicators
            "serious": report.get("serious"),
            "seriousnessdeath": report.get("seriousnessdeath"),
            "seriousnesshospitalization": report.get("seriousnesshospitalization"),
            "seriousnesslifethreatening": report.get("seriousnesslifethreatening"),
            "seriousnessdisabling": report.get("seriousnessdisabling"),
            # Location
            "occurcountry": report.get("occurcountry"),
            "primarysourcecountry": report.get("primarysourcecountry"),
            # Dates
            "transmissiondate": report.get("transmissiondate"),
            "receivedate": report.get("receivedate"),
        }

        # Patient information (essential fields only)
        patient = report.get("patient", {})
        if patient:
            essential_patient = {
                "patientsex": patient.get("patientsex"),
                "patientagegroup": patient.get("patientagegroup"),
                "patientonsetage": patient.get("patientonsetage"),
                "patientonsetageunit": patient.get("patientonsetageunit"),
                "patientweight": patient.get("patientweight"),
            }

            # Drugs (essential fields only, no openfda metadata)
            drugs = patient.get("drug", [])
            if drugs:
                essential_drugs = []
                for drug in drugs:
                    essential_drug = {
                        "medicinalproduct": drug.get("medicinalproduct"),
                        "drugindication": drug.get("drugindication"),
                        "drugadministrationroute": drug.get("drugadministrationroute"),
                        "drugdosagetext": drug.get("drugdosagetext"),
                        "drugdosageform": drug.get("drugdosageform"),
                        "drugstartdate": drug.get("drugstartdate"),
                        "actiondrug": drug.get("actiondrug"),
                    }
                    # Only include non-empty fields
                    essential_drug = {
                        k: v for k, v in essential_drug.items() if v is not None
                    }
                    if essential_drug:
                        essential_drugs.append(essential_drug)
                if essential_drugs:
                    essential_patient["drug"] = essential_drugs

            # Reactions (all fields are essential)
            reactions = patient.get("reaction", [])
            if reactions:
                essential_reactions = []
                for reaction in reactions:
                    essential_reaction = {
                        "reactionmeddrapt": reaction.get("reactionmeddrapt"),
                        "reactionmeddraversionpt": reaction.get(
                            "reactionmeddraversionpt"
                        ),
                        "reactionoutcome": reaction.get("reactionoutcome"),
                    }
                    # Only include non-empty fields
                    essential_reaction = {
                        k: v for k, v in essential_reaction.items() if v is not None
                    }
                    if essential_reaction:
                        essential_reactions.append(essential_reaction)
                if essential_reactions:
                    essential_patient["reaction"] = essential_reactions

            # Summary if available
            if "summary" in patient:
                essential_patient["summary"] = patient["summary"]

            essential["patient"] = essential_patient

        # Remove None values
        essential = {k: v for k, v in essential.items() if v is not None}
        return essential

    def _extract_custom_fields(self, report, field_config):
        """
        Extract fields based on custom configuration.
        field_config can be a list of field paths or a dict with inclusion rules.
        """
        if isinstance(field_config, list):
            # Simple list of field paths to include
            result = {}
            for field_path in field_config:
                value = self._get_nested_value(report, field_path)
                if value is not None:
                    self._set_nested_value(result, field_path, value)
            return result
        else:
            # Use default extraction
            return self._extract_essential_fields(report)

    def _get_nested_value(self, obj, path):
        """Get value from nested dict using dot notation path"""
        parts = path.split(".")
        value = obj
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list) and part.isdigit():
                value = value[int(part)] if int(part) < len(value) else None
            else:
                return None
            if value is None:
                return None
        return value

    def _set_nested_value(self, obj, path, value):
        """Set value in nested dict using dot notation path"""
        parts = path.split(".")
        current = obj
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    def _map_value(self, param_name, value):
        # Special handling for seriousness fields: if value is "No", skip this field
        seriousness_fields = {
            "seriousnessdeath",
            "seriousnesshospitalization",
            "seriousnessdisabling",
            "seriousnesslifethreatening",
            "seriousnessother",
        }
        if param_name in seriousness_fields:
            if value == "No":
                return None, None  # Signal to skip this field
            # Feature-66B-005: also accept native openFDA integer 1 or string "1" as "Yes"
            if value in ("Yes", 1, "1"):
                return None, "1"
            # If not Yes/No/1, error
            return (
                f"Invalid value '{value}' for '{param_name}'. Allowed values: ['Yes'] (omit to include all).",
                None,
            )

        if param_name in HUMAN_TO_FDA_MAP:
            value_map = HUMAN_TO_FDA_MAP[param_name]
            if value not in value_map:
                print("No mapping found for value:", value, "skipping")
                allowed_values = list(value_map.keys())
                return (
                    f"Invalid value '{value}' for '{param_name}'. Allowed values: {allowed_values}",
                    None,
                )
            return None, value_map[value]
        return None, value
