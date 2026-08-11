import re
import time
from copy import deepcopy
from urllib.parse import urljoin
from .restful_tool import RESTfulTool, execute_RESTful_query
from .tool_registry import register_tool

_ESSIE_OPERATOR_RE = re.compile(r'"|[()\[\]]|\b(?:AND|OR|NOT|AREA)\b', re.IGNORECASE)


def _phrase_quote_if_plain(value: str) -> str:
    """Fix-R9D-1: CTG API v2's Essie search engine treats an unquoted
    multi-word query.cond/query.intr value as an implicit-OR keyword match
    rather than a phrase, so "cervical cancer" ranks unrelated head/neck
    and esophageal trials above actual cervical cancer trials (confirmed
    live: 11215 unquoted matches vs. 2519 when phrase-quoted, with the
    quoted results correctly topped by cervical-cancer-specific trials).
    Quoting the value as an Essie phrase fixes this -- but only for a
    plain multi-word value with no existing quotes/parens/boolean
    operators, since query_cond's own docs advertise Boolean-operator
    support (e.g. "breast cancer AND HER2") that a blind wrap would
    break."""
    if " " in value and not _ESSIE_OPERATOR_RE.search(value):
        return f'"{value}"'
    return value


def _restrict_to_area(value: str, areas: tuple) -> str:
    """Fix-R13B-1: CTG API v2's Essie search engine treats a bare
    query.intr/query.spons value as a match against the whole study
    record (brief summaries, arm descriptions, eligibility text, etc.)
    rather than restricting to the actual intervention-name or
    lead-sponsor-name field, so a specific query like 'vedolizumab' or
    'Takeda' surfaces completely unrelated trials -- confirmed live: an
    oncology trial with no vedolizumab intervention ranked in the
    query.intr top 5 (215 unrestricted hits vs. 134 once restricted, all
    correctly containing the drug), and a Neurocrine/Shire-sponsored
    trial ranked in the query.spons top 5 for 'Takeda' (1977 unrestricted
    hits vs. 1022 once restricted, all correctly Takeda-sponsored).
    Wrapping the value in Essie's AREA[<area>] operator (and
    phrase-quoting multi-word values, same as _phrase_quote_if_plain)
    fixes this -- but only for a plain value with no existing Essie
    syntax, since advanced users may already supply their own
    AREA/boolean operators.

    Fix-R23-1: restricting an intervention query to AREA[InterventionName]
    *alone* went too far the other way. Registrants record brand names in
    the separate InterventionOtherName (synonym) field, so a brand-name
    query all but vanished while its generic returned a full set --
    confirmed live: 'Eliquis' + atrial fibrillation matched 5 trials on
    InterventionName vs. 43 once other-names are included, and 'Opdualag'
    + melanoma went 2 -> 19. Searching both name fields recovers those
    without reopening R13B-1's hole, since the noise it removed came from
    description/arm-label text that neither name field contains (checked
    against the unrestricted counts: vedolizumab 134 -> 142 vs. 215
    unrestricted, apixaban 96 -> 108 vs. 189)."""
    if _ESSIE_OPERATOR_RE.search(value):
        return value
    quoted = _phrase_quote_if_plain(value)
    clauses = [f"AREA[{area}]{quoted}" for area in areas]
    if len(clauses) == 1:
        return clauses[0]
    return "(" + " OR ".join(clauses) + ")"


# Feature-R33-1: the two helpers above rewrite the caller's wording before it
# is sent -- a plain multi-word value becomes an exact Essie phrase, and an
# intervention/sponsor is further narrowed to specific AREA[] fields. Both
# rewrites are deliberate and load-bearing (they are what keeps 'cervical
# cancer' and 'vedolizumab' precise), but they create a hazard the caller
# cannot see: the query that runs is not the query that was asked for, so a
# rewrite that matches nothing comes back as an ordinary, successful "0
# studies". Confirmed live: intervention='donor derived cell therapy' executes
# as (AREA[InterventionName]"donor derived cell therapy" OR
# AREA[InterventionOtherName]"donor derived cell therapy") with totalCount 0,
# while the phrase the caller actually typed has 251 matches on a plain
# query.intr; condition='kidney transplantation' executes quoted for 2436
# against 2863 unquoted. The answer is disclosure, not removal -- removing the
# quoting would just trade a silent false negative for the silent false
# positives R9D-1/R13B-1/R23-1 were fixing. So every search reports the query
# it really executed, and a zero that followed a rewrite is checked against the
# caller's original wording and told apart from a genuine absence of trials.
def _describe_rewrite(parameter, api_field, submitted, executed, areas=()):
    """Record one query rewrite so the response can disclose it."""
    return {
        "parameter": parameter,
        "api_field": api_field,
        "submitted": submitted,
        "executed": executed,
        "restricted_to_fields": list(areas),
    }


def _relaxed_match_check(params, rewrites, fetch_total_count):
    """Ask ClinicalTrials.gov whether the caller's original wording would have
    matched, so an empty result set becomes self-diagnosing.

    Issued only after a rewritten query returned nothing, so the common path
    pays for no extra request. The relaxed result set is deliberately *not*
    swapped in: the caller asked for the strict query and still gets exactly
    the studies it matched. What changes is that a false negative now says so
    and names the escape hatch instead of being discovered downstream.

    A parenthesised value is that escape hatch: both rewrite helpers bail out
    on any Essie syntax, so '(donor derived cell therapy)' reaches the API
    verbatim and matches the same 251 studies as the loose form.
    """
    relaxed = {rw["api_field"]: rw["submitted"] for rw in rewrites}
    probe = dict(params)
    probe.update(relaxed)
    # Every other filter is inherited from the real query so the two counts are
    # comparable; only the count is read, so ask for the cheapest possible body
    # (one study, one field: 167 bytes against 62 KB for the default full
    # protocolSection).
    probe["pageSize"] = 1
    probe["countTotal"] = "true"
    probe["fields"] = "NCTId"
    probe.pop("pageToken", None)

    try:
        total = fetch_total_count(probe)
        failure = None if total is not None else "it returned no usable response"
    except Exception as exc:  # transport, HTTP or decode failure
        total, failure = None, f"{type(exc).__name__}: {exc}"

    check = {"relaxed_query": relaxed, "relaxed_total_count": total}
    if failure:
        # Degrade rather than turn a working call into an error: the studies
        # above are still whatever the strict query matched.
        check["note"] = (
            "This search rewrote your wording (see query_rewrites) and matched "
            "0 studies. Whether your original wording would have matched could "
            f"not be checked ({failure}), so treat this 0 as unverified rather "
            "than as evidence that no such trials exist."
        )
    elif total:
        hints = "; ".join(
            f'pass {rw["parameter"]}="({rw["submitted"]})" to send your '
            "wording verbatim"
            for rw in rewrites
        )
        check["note"] = (
            "LIKELY FALSE NEGATIVE: the rewritten query matched 0 studies, but "
            f"your original wording matches {total} on ClinicalTrials.gov. The "
            "empty studies list above is a consequence of the rewrite, not "
            f"evidence that no such trials exist. To retrieve those {total}: "
            f"{hints} (parenthesised values are passed through unmodified). "
            "For a free-text search across every study field instead, use "
            "ClinicalTrials_search_studies with query_term."
        )
    else:
        check["note"] = (
            "Your original wording also matches 0 studies on "
            "ClinicalTrials.gov, so this 0 reflects a genuine absence of "
            "matching trials rather than an artifact of the query rewrite."
        )
    return check


def _executed_query(params):
    """The subset of the outgoing parameters that decides which studies match."""
    return {k: v for k, v in params.items() if k.startswith(("query.", "filter."))}


# Fix-R23-2: CTG API v2 rejects anything but its exact upper-snake enum
# spellings, and it does so with a bare HTTP 400 whose remediation reads
# "Retry the request / Check service status / Report issue if persistent" --
# advice that is actively wrong when the caller simply typed
# filter_status='recruiting' or filter_phase='Phase 3'. Both are the natural
# spellings (and 'Phase 3' is how ClinicalTrials.gov renders it on screen), so
# normalize them here and reject anything genuinely unknown at input with the
# legal values named, rather than letting a user-input error come back dressed
# as a service outage.
_CTG_STATUS_VALUES = (
    "ACTIVE_NOT_RECRUITING",
    "APPROVED_FOR_MARKETING",
    "AVAILABLE",
    "COMPLETED",
    "ENROLLING_BY_INVITATION",
    "NO_LONGER_AVAILABLE",
    "NOT_YET_RECRUITING",
    "RECRUITING",
    "SUSPENDED",
    "TEMPORARILY_NOT_AVAILABLE",
    "TERMINATED",
    "UNKNOWN",
    "WITHDRAWN",
    "WITHHELD",
)

_CTG_PHASE_VALUES = (
    "EARLY_PHASE1",
    "NA",
    "PHASE1",
    "PHASE2",
    "PHASE3",
    "PHASE4",
)


def _canonicalize_enum(value: str, allowed: tuple):
    """Map a loosely-spelled enum value onto its exact CTG spelling.

    Comparison ignores case and every non-alphanumeric separator, so
    'recruiting', 'Active, not recruiting' and 'Phase 3' all resolve.
    Returns None when the value matches nothing, so the caller can raise a
    validation error naming the legal set.
    """

    def _key(v):
        return "".join(ch for ch in str(v).upper() if ch.isalnum())

    return {_key(a): a for a in allowed}.get(_key(value))


@register_tool("ClinicalTrialsTool")
class ClinicalTrialsTool(RESTfulTool):
    _BASE_URL = "https://clinicaltrials.gov/api/v2"

    # The two auxiliary /stats lookups behind the field-values coverage note are
    # enrichment, not the answer, so they get a tighter timeout than the primary
    # request and a short memo of their own failures (see _cached_aux_lookup).
    _AUX_LOOKUP_TIMEOUT = 10
    _AUX_FAILURE_TTL = 60

    _OPERATION_URLS = {
        "search": "/studies",
        "get_study": "/studies",
        "stats_size": "/stats/size",
        "field_values": "/stats/field-values",
    }

    def __init__(self, tool_config):
        base_url = self._BASE_URL
        self._operation = (tool_config.get("fields") or {}).get("operation")

        if "tool_url" in tool_config:
            url_path = tool_config["tool_url"]
        else:
            url_path = self._OPERATION_URLS.get(self._operation, "/studies")

        full_url = urljoin(base_url + "/", url_path.lstrip("/"))
        super().__init__(tool_config, full_url)

        self.list_params_to_join = [
            "filter.ids",
            "filter.overallStatus",
            "fields",
            "sort",
        ]

        self.param_name_mapper = {
            "condition": "query.cond",
            "title": "query.titles",
            "intervention": "query.intr",
            "outcome": "query.outc",
            "overall_status": "filter.overallStatus",
            "query_term": "query.term",
            "query": "query.term",  # alias: agents naturally pass 'query'
            "status": "filter.overallStatus",  # alias: agents naturally pass 'status'
            "max_results": "pageSize",  # alias: agents naturally pass 'max_results'
            "limit": "pageSize",  # alias: agents naturally pass 'limit'
            "keyword": "query.term",  # alias: agents naturally pass 'keyword'
        }

    def _map_param_names(self, arguments):
        """
        Maps the parameter names in the arguments dictionary to the expected parameter names defined in the tool's JSON configuration.

        Args:
            arguments (dict): Runtime arguments provided to the tool's run method.

        Returns
            dict: A new dictionary with mapped parameter names.
        """

        mapped_arguments = {}
        for key, value in arguments.items():
            if key in self.param_name_mapper:
                mapped_key = self.param_name_mapper[key]
                mapped_arguments[mapped_key] = value
            else:
                mapped_arguments[key] = value
        return mapped_arguments

    def _prepare_api_params(self, arguments):
        """
        Prepares the dictionary of parameters for the API query string based on tool config and runtime arguments.

        Args:
            arguments (dict): Runtime arguments provided to the tool's run method.

        Returns
            dict: A dictionary of parameters ready for the API requests.
        """
        api_params = {}

        for param_name, value in arguments.items():
            if value is not None:
                # Handle parameters defined as lists that need joining
                if param_name in self.list_params_to_join and isinstance(value, list):
                    # Join list items into a comma-separated string
                    api_params[param_name] = ",".join(map(str, value))
                else:
                    api_params[param_name] = value

        return api_params

    def _format_endpoint_url(self, arguments):
        """
        Formats the endpoint URL by substituting path parameters (like {nctId}) with values from the arguments dictionary.

        Args:
            arguments (dict): Runtime arguments provided to the tool's run method.

        Returns
            str: The formatted endpoint URL.
        """
        url_to_format = self.endpoint_url
        try:
            # Find keys in arguments that match placeholders in the URL template
            # e.g., if url_to_format is ".../studies/{nctId}", find 'nctId' in arguments
            path_params = {
                k: v for k, v in arguments.items() if f"{{{k}}}" in url_to_format
            }
            # Perform the substitution
            return url_to_format.format(**path_params)
        except KeyError as e:
            # This might happen if a placeholder exists but the corresponding key is missing in arguments
            print(
                f"Warning: Missing key {e} in arguments for URL formatting: {url_to_format}"
            )
            # Return the original URL; the API call will likely fail, but avoids crashing here
            return url_to_format

    def run(self, arguments):
        if not self._operation:
            raise NotImplementedError(
                "The run method should be implemented in subclasses."
            )
        if self._operation == "search":
            result = self._run_search(arguments)
        elif self._operation == "get_study":
            result = self._run_get_study(arguments)
        elif self._operation == "stats_size":
            result = self._run_stats_size(arguments)
        elif self._operation == "field_values":
            result = self._run_field_values(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {self._operation}"}

        if isinstance(result, dict) and "status" not in result:
            if "error" in result:
                return {"status": "error", **result}
            return {"status": "success", **result}
        return result

    # Essie fields that get restricted via AREA[<name>] rather than a plain
    # value match (see _restrict_to_area). Keyed by the mapped API param name.
    _AREA_RESTRICTED_FIELDS = {
        # InterventionOtherName holds registrant-supplied synonyms, which is
        # where brand names live (see Fix-R23-1 in _restrict_to_area).
        "query.intr": ("InterventionName", "InterventionOtherName"),
        "query.spons": ("LeadSponsorName",),
    }

    def _fetch_total_count(self, probe_params):
        """Count-only request used by the relaxed-wording check."""
        import requests

        probe = requests.get(
            f"{self._BASE_URL}/studies", params=probe_params, timeout=30
        )
        probe.raise_for_status()
        return probe.json().get("totalCount")

    def _attach_disclosure(self, result_data, params, query_rewrites):
        """Feature-R33-1: record what actually ran, and diagnose an empty result.

        Shared by both search paths on purpose. Feature-27A-1 was caused by
        exactly this kind of logic existing once per path and drifting; keeping
        the trigger condition and the key names in one place is what stops the
        two tools disagreeing about what they disclose.
        """
        result_data["executed_query"] = _executed_query(params)
        result_data["query_rewrites"] = query_rewrites
        if not result_data.get("studies") and query_rewrites:
            result_data["relaxed_match_check"] = _relaxed_match_check(
                params, query_rewrites, self._fetch_total_count
            )
        return result_data

    def _run_search(self, arguments):
        """Handle search operations (search_studies, search_by_intervention, search_by_sponsor)."""
        import requests

        _SEARCH_PARAM_MAP = {
            "query_cond": "query.cond",
            "query_intr": "query.intr",
            "query_term": "query.term",
            "filter_status": "filter.overallStatus",
            "page_size": "pageSize",
            "next_page_token": "pageToken",
            "intervention": "query.intr",
            "sponsor": "query.spons",
            # Natural aliases
            "condition": "query.cond",
            "status": "filter.overallStatus",
            "query": "query.term",
            "keyword": "query.term",
            "max_results": "pageSize",
            "limit": "pageSize",
        }

        params = {"format": "json", "countTotal": "true"}
        # Note: v1-style field names like EnrollmentCount, InterventionName,
        # LeadSponsorName are not recognized by the v2 API. Omitting 'fields'
        # returns the full protocolSection which our parsing code handles.

        # Build advanced filter clauses (filter.advanced for phase/studytype)
        advanced_clauses = []
        # Feature-R33-1: every value the two helpers below alter is recorded so
        # the response can show what actually ran, keyed by the name the caller
        # used rather than the API's.
        query_rewrites = []

        for key, value in arguments.items():
            if value is None:
                continue
            if key == "filter_phase":
                # CTG API v2 uses filter.advanced for phase, not filter.phase
                phases = []
                for raw in str(value).split(","):
                    raw = raw.strip()
                    if not raw:
                        continue
                    canonical = _canonicalize_enum(raw, _CTG_PHASE_VALUES)
                    if canonical is None:
                        return {
                            "status": "error",
                            "error": (
                                f"Invalid filter_phase value '{raw}'. "
                                f"Valid values are: {', '.join(_CTG_PHASE_VALUES)}. "
                                "Comma-separate to combine (e.g. 'PHASE2,PHASE3')."
                            ),
                        }
                    phases.append(canonical)
                if not phases:
                    continue
                phase_clause = " OR ".join(f"AREA[Phase]{p}" for p in phases)
                if len(phases) > 1:
                    phase_clause = f"({phase_clause})"
                advanced_clauses.append(phase_clause)
            elif key == "filter_study_type":
                # CTG API v2 uses filter.advanced for study type, not filter.studyType
                study_types = [s.strip() for s in value.split(",")]
                study_type_clause = " OR ".join(
                    f"AREA[StudyType]{s}" for s in study_types
                )
                if len(study_types) > 1:
                    study_type_clause = f"({study_type_clause})"
                advanced_clauses.append(study_type_clause)
            elif key in _SEARCH_PARAM_MAP:
                mapped_key = _SEARCH_PARAM_MAP[key]
                if mapped_key == "filter.overallStatus":
                    statuses = []
                    raw_values = (
                        value if isinstance(value, list) else str(value).split(",")
                    )
                    for raw in raw_values:
                        raw = str(raw).strip()
                        if not raw:
                            continue
                        canonical = _canonicalize_enum(raw, _CTG_STATUS_VALUES)
                        if canonical is None:
                            return {
                                "status": "error",
                                "error": (
                                    f"Invalid status value '{raw}'. Valid values "
                                    f"are: {', '.join(_CTG_STATUS_VALUES)}. "
                                    "Comma-separate to combine."
                                ),
                            }
                        statuses.append(canonical)
                    if not statuses:
                        continue
                    value = ",".join(statuses)
                elif mapped_key == "query.cond" and isinstance(value, str):
                    rewritten = _phrase_quote_if_plain(value)
                    if rewritten != value:
                        query_rewrites.append(
                            _describe_rewrite(key, mapped_key, value, rewritten)
                        )
                    value = rewritten
                elif mapped_key in self._AREA_RESTRICTED_FIELDS and isinstance(
                    value, str
                ):
                    areas = self._AREA_RESTRICTED_FIELDS[mapped_key]
                    rewritten = _restrict_to_area(value, areas)
                    # An unchanged value means the caller supplied their own
                    # Essie syntax, which both helpers deliberately leave
                    # alone -- nothing was rewritten, so nothing to disclose.
                    if rewritten != value:
                        query_rewrites.append(
                            _describe_rewrite(key, mapped_key, value, rewritten, areas)
                        )
                    value = rewritten
                params[mapped_key] = value

        if advanced_clauses:
            params["filter.advanced"] = " AND ".join(advanced_clauses)

        resp = requests.get(f"{self._BASE_URL}/studies", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        studies = []
        for s in data.get("studies", []):
            proto = s.get("protocolSection", {})
            # Fix-R23-3: the intervention list is capped at 5 for brevity, but
            # it used to be sliced with no count and no flag -- so a study that
            # genuinely matched the queried drug could come back listing five
            # *other* interventions and read as a false positive (e.g.
            # NCT03337698 is a real tiragolumab trial with 18 interventions,
            # none of which survived the slice). Report the true count so a
            # short list can be told apart from a truncated one.
            all_interventions = [
                iv.get("name")
                for iv in proto.get("armsInterventionsModule", {}).get(
                    "interventions", []
                )
                if iv.get("name")
            ]
            studies.append(
                {
                    "nct_id": proto.get("identificationModule", {}).get("nctId"),
                    "brief_title": proto.get("identificationModule", {}).get(
                        "briefTitle"
                    ),
                    "status": proto.get("statusModule", {}).get("overallStatus"),
                    "study_type": proto.get("designModule", {}).get("studyType"),
                    "phases": proto.get("designModule", {}).get("phases", []),
                    "enrollment": (
                        proto.get("designModule", {}).get("enrollmentInfo") or {}
                    ).get("count"),
                    "conditions": proto.get("conditionsModule", {}).get(
                        "conditions", []
                    ),
                    "interventions": all_interventions[:5],
                    "intervention_count": len(all_interventions),
                    "interventions_truncated": len(all_interventions) > 5,
                    "sponsor": (
                        proto.get("sponsorCollaboratorsModule", {}).get("leadSponsor")
                        or {}
                    ).get("name"),
                    "start_date": (
                        proto.get("statusModule", {}).get("startDateStruct") or {}
                    ).get("date"),
                    "completion_date": (
                        proto.get("statusModule", {}).get("completionDateStruct") or {}
                    ).get("date"),
                }
            )

        result_data = {
            "studies": studies,
            # totalCount may be absent from API response; fallback to len(studies)
            "total_count": data.get("totalCount") or len(studies),
            "next_page_token": data.get("nextPageToken"),
        }
        self._attach_disclosure(result_data, params, query_rewrites)

        return {
            "status": "success",
            "data": result_data,
            "metadata": {"source": "ClinicalTrials.gov API v2", "operation": "search"},
        }

    def _run_get_study(self, arguments):
        """Get full details for a single study by NCT ID."""
        import requests

        nct_id = arguments.get("nct_id")
        if not nct_id:
            return {"status": "error", "error": "nct_id is required"}

        resp = requests.get(
            f"{self._BASE_URL}/studies/{nct_id}",
            params={"format": "json"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        proto = data.get("protocolSection", {})

        study = {
            "nct_id": proto.get("identificationModule", {}).get("nctId"),
            "brief_title": proto.get("identificationModule", {}).get("briefTitle"),
            "official_title": proto.get("identificationModule", {}).get(
                "officialTitle"
            ),
            "status": proto.get("statusModule", {}).get("overallStatus"),
            "study_type": proto.get("designModule", {}).get("studyType"),
            "phases": proto.get("designModule", {}).get("phases", []),
            "enrollment": (
                proto.get("designModule", {}).get("enrollmentInfo") or {}
            ).get("count"),
            "brief_summary": proto.get("descriptionModule", {}).get("briefSummary"),
            "conditions": proto.get("conditionsModule", {}).get("conditions", []),
            "interventions": [
                {"type": i.get("type"), "name": i.get("name")}
                for i in proto.get("armsInterventionsModule", {}).get(
                    "interventions", []
                )
            ],
            "primary_outcomes": [
                {"measure": o.get("measure"), "timeFrame": o.get("timeFrame")}
                for o in proto.get("outcomesModule", {}).get("primaryOutcomes", [])
            ],
            "eligibility_criteria": proto.get("eligibilityModule", {}).get(
                "eligibilityCriteria"
            ),
            "sponsor": (
                proto.get("sponsorCollaboratorsModule", {}).get("leadSponsor") or {}
            ).get("name"),
            "locations": [
                {
                    "facility": loc.get("facility"),
                    "city": loc.get("city"),
                    "country": loc.get("country"),
                }
                for loc in proto.get("contactsLocationsModule", {}).get("locations", [])
            ],
            "references": proto.get("referencesModule", {}).get("references", []),
        }

        return {
            "status": "success",
            "data": study,
            "metadata": {
                "source": "ClinicalTrials.gov API v2",
                "operation": "get_study",
            },
        }

    def _run_stats_size(self, arguments, timeout=30):
        """Get aggregate ClinicalTrials.gov database statistics.

        `timeout` is overridden only by `_registry_total_studies`, which calls
        this for an optional denominator and should not make the caller wait
        the full primary-request budget for it.
        """
        import requests

        resp = requests.get(f"{self._BASE_URL}/stats/size", timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        # Fix-R19-2: this read `totalStudiesCount` and `averageByteSize`, neither
        # of which ClinicalTrials.gov has ever returned. The real keys on
        # /api/v2/stats/size are `totalStudies` and `averageSizeBytes` (confirmed
        # live: keys are totalStudies, averageSizeBytes, percentiles, ranges,
        # largestStudies). Both fields therefore came back null on every call
        # while `largest_studies` populated from the correctly-named
        # `largestStudies`, so the tool looked healthy and served nulls as data.
        # The legacy names are kept only as fallbacks; they are never expected
        # to hit. `percentiles`/`ranges` were parsed and discarded even though
        # the tool advertises "size distribution" -- surface them too.
        total_studies = data.get("totalStudies")
        if total_studies is None:
            total_studies = data.get("totalStudiesCount") or data.get("studiesCount")
        average_byte_size = data.get("averageSizeBytes")
        if average_byte_size is None:
            average_byte_size = data.get("averageByteSize")

        return {
            "status": "success",
            "data": {
                "total_studies": total_studies,
                "average_byte_size": average_byte_size,
                "byte_size_percentiles": data.get("percentiles", {}),
                "size_ranges": data.get("ranges", []),
                "largest_studies": data.get("largestStudies"),
            },
            "metadata": {
                "source": "ClinicalTrials.gov API v2",
                "operation": "stats_size",
            },
        }

    def _run_field_values(self, arguments):
        """Get value distribution for a specific field."""
        import requests

        field = arguments.get("field")
        if not field:
            return {"status": "error", "error": "field is required"}

        # Fix-R36-1: `query_cond` was forwarded as `query.cond` and made every
        # such call a hard 400 -- the tool advertised a condition filter the
        # endpoint has never had. ClinicalTrials.gov's field-value statistics
        # endpoint takes exactly two parameters, `fields` and `types`; the
        # OpenAPI description of `fieldValuesStats` lists no others, and the
        # live API rejects each alternative spelling we probed:
        #   ?fields=StdAge&query.cond=asthma            -> 400 "Invalid prefix in parameter name: query.cond"
        #   ?fields=StdAge&filter.overallStatus=...     -> 400 "Invalid prefix in parameter name: filter.overallStatus"
        #   ?fields=StdAge&filter.advanced=AREA[...]    -> 400 "Invalid prefix in parameter name: filter.advanced"
        #   ?fields=StdAge&cond=asthma                  -> 400 "`cond` is unknown parameter"
        #   ?fields=StdAge&query=asthma                 -> 400 "`query` is unknown parameter"
        #   ?fields=StdAge&aggFilters=phase:3           -> 400 "`aggFilters` is unknown parameter"
        # (identical on the /stats/field/values alias). There is therefore no
        # filtered form to implement, so the argument is rejected before the
        # request is built and the caller is pointed at the route that does
        # work instead of getting an opaque upstream 400.
        if arguments.get("query_cond"):
            return {
                "status": "error",
                "error": (
                    "ClinicalTrials.gov cannot filter field-value counts: the "
                    "/stats/fieldValues endpoint counts values across the entire "
                    "registry and accepts only 'fields' and 'types'. Any condition, "
                    "status or phase filter is rejected upstream with HTTP 400 "
                    "('Invalid prefix in parameter name: query.cond'), so 'query_cond' "
                    f"cannot restrict counts for '{field}'. Either (1) re-run this tool "
                    "without query_cond for registry-wide counts, or (2) for counts "
                    "restricted to a condition, call ClinicalTrials_search_studies with "
                    f"query_cond={arguments['query_cond']!r} and page_size up to 1000, "
                    "then tally the per-study fields it returns (status, phases, "
                    "study_type, sponsor, conditions). Fields outside that set (for "
                    "example StdAge) are not returned per study by any ClinicalTrials "
                    "tool and so cannot be counted per condition."
                ),
            }

        # Fix-R37-1 (page_size): `page_size` has been declared and documented
        # ("Number of field values to return (default 50)") since the tool was
        # written, but nothing ever read it -- {"field":"Phase","page_size":2}
        # returned all 6 rows and {"field":"OverallStatus","page_size":3} all 14.
        # Silently accepting a documented parameter and ignoring it is the worst
        # of both worlds: the caller believes the list was capped and cannot tell
        # a full facet from a truncated one. It is honoured below, and when it
        # actually cuts rows the response says so rather than leaving a partial
        # list looking whole.
        page_size = arguments.get("page_size")
        if page_size is None:
            page_size = 50
        try:
            page_size = int(page_size)
        except (TypeError, ValueError):
            return {
                "status": "error",
                "error": (f"page_size must be a positive integer, got {page_size!r}."),
            }
        if page_size < 1:
            return {
                "status": "error",
                "error": (
                    f"page_size must be a positive integer, got {page_size}. "
                    "Omit it to return up to the default 50 values."
                ),
            }

        # CTG API v2: endpoint is /stats/fieldValues (camelCase), param is 'fields' (plural)
        params = {"fields": field}

        resp = requests.get(
            f"{self._BASE_URL}/stats/fieldValues", params=params, timeout=30
        )
        resp.raise_for_status()
        data = resp.json()  # Returns a list of field objects

        field_obj = data[0] if isinstance(data, list) and data else {}
        if not isinstance(field_obj, dict):
            field_obj = {}
        all_values = [
            {"value": item.get("value"), "studies_count": item.get("studiesCount")}
            for item in field_obj.get("topValues") or []
        ]

        # Fix-R37-1 (denominator): the response used to be the rows and nothing
        # else, discarding the two numbers upstream sends alongside them --
        # `missingStudiesCount` and `uniqueValuesCount`. For Phase that threw
        # away 141,728: an analyst reading "PHASE3 49,625" divided by the 480,714
        # the rows sum to and got 10.3%, with no way to learn that 141,728
        # studies were never in the facet at all. Both are surfaced now, together
        # with the registry total, so the caller has a real denominator.
        unique_values_count = field_obj.get("uniqueValuesCount")
        if not isinstance(unique_values_count, int):
            unique_values_count = len(all_values)
        missing_studies_count = field_obj.get("missingStudiesCount")
        if not isinstance(missing_studies_count, int):
            missing_studies_count = None
        field_path = field_obj.get("field")

        values = all_values[:page_size]
        # Two independent truncations. ClinicalTrials.gov caps `topValues` on its
        # own for high-cardinality fields (Condition returns the top 250 of
        # 132,704 distinct values), which no page_size can lift; page_size cuts
        # further on our side. Distinguishing them matters because only the
        # second is the caller's to undo.
        upstream_truncated = len(all_values) < unique_values_count
        page_truncated = len(values) < len(all_values)
        rows_sum = sum(
            v["studies_count"]
            for v in all_values
            if isinstance(v["studies_count"], int)
        )

        total_studies = self._registry_total_studies()
        is_multi_valued = self._is_multi_valued_field(field_path)

        studies_with_value = None
        if isinstance(total_studies, int) and isinstance(missing_studies_count, int):
            studies_with_value = total_studies - missing_studies_count

        # How many studies are counted in more than one row. Only derivable when
        # the rows are the WHOLE facet -- with an upstream-truncated ranking
        # rows_sum is a partial sum and the subtraction is meaningless.
        duplicate_studies_count = None
        if (
            not upstream_truncated
            and isinstance(total_studies, int)
            and isinstance(missing_studies_count, int)
        ):
            excess = rows_sum + missing_studies_count - total_studies
            duplicate_studies_count = excess if excess >= 0 else None

        return {
            "status": "success",
            "data": {
                "field": field,
                "field_path": field_path,
                "field_type": field_obj.get("type"),
                "values": values,
                # Fix-R37-1 (naming): this used to be `total_count`, holding the
                # number of ROWS returned -- while `total_count` in the sibling
                # ClinicalTrials_search_studies holds the number of matching
                # STUDIES. One name, two incompatible meanings in one tool
                # family, and the wrong reading (studies) is the plausible one.
                #
                # Only THIS side is renamed, deliberately. Across the repo
                # `total_count` overwhelmingly means "records matching the
                # query" (orphanet, cosmic, sabiork, clinvar, ...), which is
                # exactly what _run_search and ClinicalTrialsSearchTool already
                # emit -- they hold the conventional meaning and renaming them
                # would break the convention rather than restore it. The facet
                # row count was the outlier, so the outlier moves. No alias is
                # kept under the old name: an alias would preserve the very
                # ambiguity being removed, and both quantities the single key
                # conflated are below under names that say which they are.
                "unique_values_count": unique_values_count,
                "values_returned": len(values),
                "truncated": page_truncated or upstream_truncated,
                "missing_studies_count": missing_studies_count,
                "total_studies_in_registry": total_studies,
                "studies_with_value": studies_with_value,
                "is_multi_valued": is_multi_valued,
                "duplicate_studies_count": duplicate_studies_count,
                "coverage_note": self._field_values_coverage_note(
                    field=field,
                    field_path=field_path,
                    rows_sum=rows_sum,
                    missing_studies_count=missing_studies_count,
                    total_studies=total_studies,
                    studies_with_value=studies_with_value,
                    is_multi_valued=is_multi_valued,
                    duplicate_studies_count=duplicate_studies_count,
                    unique_values_count=unique_values_count,
                    values_returned=len(values),
                    upstream_values=len(all_values),
                    page_size=page_size,
                ),
            },
            "metadata": {
                "source": "ClinicalTrials.gov API v2",
                "operation": "field_values",
            },
        }

    def _list_valued_field_paths(self):
        """Field paths ClinicalTrials.gov itself reports list sizes for.

        Returns a frozenset of dotted paths, or None if the lookup failed (which
        is NOT the same as "no list fields" and must not be read as one).

        WHY this endpoint: `/stats/fieldValues` gives no hint whether a field
        holds one value per study or many, and guessing from the plural in
        `protocolSection.designModule.phases` is a naming heuristic, not a fact.
        `/stats/field/sizes` called with no `fields` parameter is the API's own
        answer: it returns exactly the 71 field paths that are lists, each with
        its size histogram, and 404s ("No field list sizes for `X` field") for
        anything scalar. Verified live against `/studies/metadata`, which types
        the same nodes with an explicit `[]` suffix and agrees on every one:
            phases        -> "type": "Phase[]"         -> in /stats/field/sizes
            interventions -> "type": "Intervention[]"  -> in /stats/field/sizes
            overallStatus -> "type": "Status"          -> 404
        """
        return self._cached_aux_lookup(
            "_list_field_paths_cache", self._fetch_list_valued_field_paths
        )

    def _fetch_list_valued_field_paths(self):
        import requests

        try:
            resp = requests.get(
                f"{self._BASE_URL}/stats/field/sizes",
                timeout=self._AUX_LOOKUP_TIMEOUT,
            )
            if resp.status_code != 200:
                return None
            payload = resp.json()
        except (requests.exceptions.RequestException, ValueError):
            return None
        if not isinstance(payload, list):
            return None

        return frozenset(
            entry["field"]
            for entry in payload
            if isinstance(entry, dict) and entry.get("field")
        )

    def _is_multi_valued_field(self, field_path):
        """Whether one study can contribute to several rows of this field's facet.

        True / False / None (could not be determined).

        Checking the field's OWN path against the list-field set is not enough,
        and getting this wrong in the safe-looking direction is how the bug
        hides. InterventionType sits at
        `protocolSection.armsInterventionsModule.interventions.type` -- a scalar
        leaf, so `/stats/field/sizes?fields=InterventionType` 404s -- yet its
        rows sum to 616,289 against 597,913 registered studies, because the
        ARRAY is the enclosing `interventions` list and a study with a drug and
        a device intervention lands in two rows. So an ancestor that is a list
        makes the leaf multi-valued too, and the prefix test below is what
        catches it.
        """
        if not field_path:
            return None
        paths = self._list_valued_field_paths()
        if paths is None:
            return None
        if field_path in paths:
            return True
        return any(field_path.startswith(f"{prefix}.") for prefix in paths)

    def _registry_total_studies(self):
        """Total studies in the registry -- the denominator the facet lacks.

        Delegates to `_run_stats_size` rather than re-issuing the same GET:
        that method already owns /stats/size, and owns in particular the
        Fix-R19-2 knowledge of which key holds the count (`totalStudies`, with
        `totalStudiesCount`/`studiesCount` kept as fallbacks after the tool
        spent a release reading a key ClinicalTrials.gov has never sent). A
        second hand-rolled parse here would be a second place for that to rot.

        Returns None rather than a guess when the lookup fails; every consumer
        degrades to prose that omits the figure instead of printing a
        fabricated one.
        """
        return self._cached_aux_lookup(
            "_registry_total_cache", self._fetch_registry_total_studies
        )

    def _fetch_registry_total_studies(self):
        import requests

        try:
            result = self._run_stats_size({}, timeout=self._AUX_LOOKUP_TIMEOUT)
        except (requests.exceptions.RequestException, ValueError):
            return None
        total = (result.get("data") or {}).get("total_studies")
        return total if isinstance(total, int) else None

    def _cached_aux_lookup(self, attr, fetch):
        """Memoise an optional enrichment lookup -- including its failures.

        Both auxiliary lookups are enrichment: the rows are already in hand and
        a failure only costs the caller a denominator. That makes the failure
        path the one worth engineering. Not caching failures at all means an
        outage of either stats endpoint charges EVERY subsequent call two fresh
        timeouts stacked on top of the primary request, for as long as it
        lasts. Caching them forever wedges the tool on a single blip. So a
        failure is remembered for a short window only: one degraded response
        per window instead of one per call, and it heals by itself.

        Successes are cached without expiry -- the registry total drifts by a
        few hundred studies a day and the set of list-valued fields changes
        with the schema, neither fast enough to matter against a process
        lifetime.
        """
        entry = getattr(self, attr, None)
        if entry is not None:
            value, expires_at = entry
            if expires_at is None or time.monotonic() < expires_at:
                return value

        value = fetch()
        expires_at = (
            None if value is not None else time.monotonic() + self._AUX_FAILURE_TTL
        )
        setattr(self, attr, (value, expires_at))
        return value

    def _field_values_coverage_note(
        self,
        field,
        field_path,
        rows_sum,
        missing_studies_count,
        total_studies,
        studies_with_value,
        is_multi_valued,
        duplicate_studies_count,
        unique_values_count,
        values_returned,
        upstream_values,
        page_size,
    ):
        """Prose stating what the rows do and do NOT sum to, and which way.

        Modelled on the FAERS count tools' `_coverage_note` in
        `openfda_adv_tool.py`, for the same reason and in the same register: a
        facet distorted in two opposite directions cannot be described by
        naming only one of them. For Phase the rows are simultaneously
        (a) SHORT by the 141,728 studies that record no phase and are excluded
        outright, and (b) LONG by the 24,529 studies that record two phases and
        are counted twice. Report only (a) and the reader inflates every share;
        report only (b) and they deflate it. Both are named, with numbers, and
        the note ends by saying which figure may be used as a denominator.
        """
        # Derived here rather than passed in: both are one comparison over
        # numbers this method already receives, and computing them twice (once
        # in the caller, once implicitly in the prose) is two places to keep in
        # step. The caller keeps its own copies only because the response has a
        # single combined `truncated` flag.
        upstream_truncated = upstream_values < unique_values_count
        page_truncated = values_returned < upstream_values
        # A study is counted more than once either because the field is
        # structurally a list, or because the arithmetic says so outright
        # (rows_sum + missing exceeding the registry total is proof, whatever
        # the structural lookup returned).
        double_counts = bool(is_multi_valued) or bool(duplicate_studies_count)
        have_total = isinstance(total_studies, int) and bool(total_studies)
        parts = []

        # 1. What was left out of the facet entirely. The stem is shared so a
        # reworded exclusion warning cannot drift between the two branches.
        if missing_studies_count is None:
            parts.append(
                f"ClinicalTrials.gov did not report how many studies record no "
                f"{field}, so the number excluded from these rows is unknown."
            )
        else:
            scope = "studies "
            tail = "."
            if have_total:
                share = missing_studies_count / total_studies * 100
                scope = (
                    f"of the {total_studies:,} studies in the registry ({share:.1f}%) "
                )
                tail = f", leaving {studies_with_value:,} studies represented."
            parts.append(
                f"ClinicalTrials.gov computes this facet only over studies that "
                f"record {field}: {missing_studies_count:,} {scope}record no "
                "value and are EXCLUDED from the rows entirely rather than "
                f"bucketed as unknown{tail}"
            )

        # 2. Whether one study can appear in several rows.
        if double_counts:
            sentence = (
                f"{field} is also multi-valued -- ClinicalTrials.gov stores it "
                f"as a list per study ({field_path}) -- so a study recording "
                "several values is counted in SEVERAL rows"
            )
            if duplicate_studies_count:
                sentence += (
                    f"; {duplicate_studies_count:,} studies record more than one "
                    "value and are counted more than once"
                )
            parts.append(sentence + ".")
        elif is_multi_valued is None:
            parts.append(
                f"Whether {field} can hold several values per study could not be "
                "determined (the ClinicalTrials.gov list-size lookup failed), so "
                "the rows may or may not count some studies more than once."
            )
        else:
            parts.append(
                f"{field} holds at most one value per study, so the rows do not "
                "double-count: they partition the studies that record it."
            )

        # 3. What the rows sum to, and what may be divided by what.
        if upstream_truncated:
            parts.append(
                f"The {upstream_values:,} rows ClinicalTrials.gov returned are "
                f"only the most common of {unique_values_count:,} distinct "
                f"values, so their sum ({rows_sum:,}) is a partial sum of an "
                "unknown fraction of the facet and is not a denominator for "
                "anything."
            )
        elif double_counts and isinstance(total_studies, int):
            parts.append(
                f"The rows sum to {rows_sum:,}, which is neither the registry "
                f"total ({total_studies:,}) nor a clean subset of it: the two "
                "distortions run in OPPOSITE directions, excluded studies "
                "pulling the sum down and double-counted studies pulling it up. "
                "That sum counts recorded values, NOT studies -- do NOT use it "
                "as a denominator and do NOT divide one row by it to obtain a "
                f"share. Use total_studies_in_registry ({total_studies:,}) for "
                "a share of all registered studies, or studies_with_value "
                f"({studies_with_value:,}) for a share of those that record "
                f"{field}; read each row as 'studies having this value', which "
                "overlap rather than partition."
            )
        elif double_counts:
            parts.append(
                f"The rows sum to {rows_sum:,}, which counts recorded values, "
                "NOT studies -- do NOT use it as a denominator and do NOT divide "
                "one row by it to obtain a share."
            )
        elif isinstance(total_studies, int):
            parts.append(
                f"The rows sum to {rows_sum:,}. Divide a row by "
                f"studies_with_value ({studies_with_value:,}) for a share of the "
                "studies that record it, or by total_studies_in_registry "
                f"({total_studies:,}) for a share of all registered studies -- "
                "the two differ by the excluded studies above."
            )
        else:
            parts.append(
                f"The rows sum to {rows_sum:,} and partition the studies that "
                f"record {field}; the registry total could not be retrieved, so "
                "no share of all registered studies can be computed here."
            )

        # 4. Whether the caller is looking at the whole list.
        if page_truncated:
            parts.append(
                f"Only the top {values_returned:,} of {upstream_values:,} "
                f"returned values are shown (page_size={page_size}); "
                f"unique_values_count ({unique_values_count:,}) is the true "
                "number of distinct values, and the omitted rows are still "
                "included in every total above."
            )

        return " ".join(parts)


@register_tool("ClinicalTrialsSearchTool")
# Searching studies (/studies)
class ClinicalTrialsSearchTool(ClinicalTrialsTool):
    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.default_params_not_shown = {
            "format": "json",  # Default format for the response
            "sort": "@relevance",  # Default sort order
            "fields": [
                "NCTId",
                "BriefTitle",
                # "OfficialTitle",
                "OverallStatus",
                # "StartDate",
                # "PrimaryCompletionDate",
                # "PrimaryOutcomeMeasure",
                # "DescriptionModule",
                "BriefSummary",
                "Condition",
                "Phase",
                # "Intervention",
                # "InterventionName",
                # "InterventionArmGroupLabel",
                # "InterventionOtherName",
                # "WhyStopped",
                # "HasResults",
            ],  # NOTE: Can change this one
            "countTotal": True,  # NOTE: Can change this one
            # Fix-T1A-002/T3A-004: this used to also require AREA[HasResults]true,
            # which silently restricted every search to trials with *posted
            # results* — undocumented, and it made the tool return "no studies
            # found" for real, findable trials that simply haven't reported
            # results yet (e.g. rivaroxaban + renal impairment, which has 11
            # matching trials on ClinicalTrials.gov, none surfaced by this
            # filter). The phase>=2 restriction stays; it matches the tool's
            # documented "Limited to trials beyond phase 1" behavior.
            "filter.advanced": "(AREA[Phase]PHASE2 OR AREA[Phase]PHASE3 OR AREA[Phase]PHASE4)",
            # TODO: Consider adding a YEAR filter for the query to remove trials that are too early? E.g., "AREA[LastUpdatePostDate]RANGE[2000-01-01,MAX]"
        }
        # "title": {
        #             "type": "string",
        #             "description": "Query for study titles using Essie expression syntax (e.g., 'lung cancer').",
        #             "required": false
        #         },
        # "outcome": {
        #             "type": "string",
        #             "description": "Query for outcome measures using Essie expression syntax (e.g., 'overall survival', 'adverse events', 'progress-free survival').",
        #             "required": false
        #         },
        # "query.locn": {
        #     "type": "string",
        #     "description": "Query for location terms using Essie expression syntax (e.g., 'California')."
        # },
        # "overall_status": {
        #             "type": "array",
        #             "description": "Filter by a list of overall study statuses (e.g., ['RECRUITING', 'COMPLETED']). ",
        #             "items": {
        #                 "type": "string",
        #                 "enum": ["ACTIVE_NOT_RECRUITING", "COMPLETED", "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING", "RECRUITING", "SUSPENDED", "TERMINATED", "WITHDRAWN", "AVAILABLE", "NO_LONGER_AVAILABLE", "TEMPORARILY_NOT_AVAILABLE", "APPROVED_FOR_MARKETING", "WITHHELD", "UNKNOWN"]
        #             },
        #             "required": false
        #         },
        # "filter.ids": {
        #     "type": "array",
        #     "description": "Filter by a list of NCT IDs (e.g., ['NCT04852770', 'NCT01728545']).",
        #     "items": {
        #         "type": "string"
        #     }
        # },
        # "sort": {
        #     "type": "array",
        #     "description": "Comma- or pipe-separated list of fields to sort by for the studies, with optional direction. The returning studies are not sorted by default. Every list item contains a field/piece name and an optional sort direction (asc for ascending or desc for descending) after colon character (e.g., ['LastUpdatePostDate:desc', 'EnrollmentCount'], [@relevance]). Default sort order varies by field type. Special value '@relevance' sorts by query relevance.",
        #     "items": {
        #         "type": "string"
        #     }
        # },
        # "fields": {
        #     "type": "array",
        #     "description": "List of fields to return (e.g., ['NCTId', 'BriefTitle', 'OverallStatus', 'Phase', 'PrimaryCompletionDate', 'PrimaryOutcomeMeasure']). By default, we look at the following fields: ['NCTId', 'BriefTitle', 'OfficialTitle', 'OverallStatus', 'StartDate', 'PrimaryCompletionDate', 'PrimaryOutcomeMeasure', 'DescriptionModule', 'Condition', 'Phase', 'WhyStopped', 'HasResults'].",
        #     "items": {
        #         "type": "string"
        #     },
        #     "required": false
        # },

    def _fetch_total_count(self, probe_params):
        """Same count-only check as the base class, over this tool's transport.

        Each path probes through the transport it already uses for its primary
        request, so the check fails the same way -- and mocks the same way -- as
        the search it is explaining.
        """
        probe = execute_RESTful_query(
            endpoint_url=self.endpoint_url, variables=probe_params
        )
        return (probe or {}).get("totalCount")

    def run(self, arguments):
        """
        Executes the search query for clinical trials.

        Args:
            arguments (dict): A dictionary containing parameters provided by the user/LLM

        Returns
            dict or str: The JSON response from the API as a dictionary,
                         or raw text for non-JSON responses, or an error dictionary.
        """
        # Feature-R33-1: keep the caller-facing spelling of each parameter, so a
        # disclosed rewrite can be described with the name they actually typed
        # rather than the API's mapped one.
        caller_names = {self.param_name_mapper.get(k, k): k for k in arguments}
        arguments = self._map_param_names(arguments)
        query_params = deepcopy(self.query_schema)
        expected_param_names = self._map_param_names(
            self.parameters
        ).keys()  # NOTE: Workaround for not having an aligned schema in the JSON config

        # Prepare API parameters from arguments
        for k in expected_param_names:
            if k in arguments and arguments[k] is not None:
                query_params[k] = arguments[k]

        # Feature-27A-1: Fix-R13B-1's AREA restriction landed only in
        # ClinicalTrialsTool._run_search, which builds its own params, so this
        # tool -- the one advertised as "the PRIMARY tool for finding clinical
        # trials" -- kept passing a bare value to query.intr. CTG API v2's
        # Essie engine matches a bare query.intr against the whole study
        # record, so intervention="Luxturna" returned exactly one study,
        # NCT07681778, an RDH12 gene-therapy trial whose only tie to Luxturna
        # is the phrase "using a method similar to approved gene therapies
        # like Luxturna" in its brief summary -- a trial for a different drug
        # and a different gene, presented as *the* match. The restriction is
        # applied here from the shared _AREA_RESTRICTED_FIELDS mapping (and
        # via the shared _restrict_to_area helper) so the two code paths
        # cannot drift apart again, which is what caused this.
        query_rewrites = []
        for mapped_key, areas in self._AREA_RESTRICTED_FIELDS.items():
            value = query_params.get(mapped_key)
            if not isinstance(value, str):
                continue
            restricted = _restrict_to_area(value, areas)
            # An unchanged value means the caller supplied their own Essie
            # syntax (AREA[...]/boolean/quotes), which _restrict_to_area
            # deliberately leaves alone -- nothing was restricted, so there
            # is nothing to report about it below either.
            if restricted != value:
                query_params[mapped_key] = restricted
                query_rewrites.append(
                    _describe_rewrite(
                        caller_names.get(mapped_key, mapped_key),
                        mapped_key,
                        value,
                        restricted,
                        areas,
                    )
                )

        # Add default parameters that are not shown in the schema.
        # filter.advanced used to be skipped whenever a status filter was set,
        # to work around its old AREA[HasResults]true clause. That clause was
        # removed above, so the skip only disabled the documented "Limited to
        # trials beyond phase 1" gate -- and it did so silently: adding the
        # narrowing overall_status=COMPLETED filter to a metformin/lactic
        # acidosis search *raised* total_count from 2 to 3 and returned a
        # disjoint set, while a RECRUITING pembrolizumab search returned 745
        # studies instead of 557, phase-1 trials included.
        for k, v in self.default_params_not_shown.items():
            if k not in query_params:
                query_params[k] = v

        # Process list parameters that need to be joined
        api_params = self._prepare_api_params(query_params)

        # Fix a bug where 'countTotal' is a boolean but should be a string as input to API
        if "countTotal" in api_params and isinstance(api_params["countTotal"], bool):
            api_params["countTotal"] = str(api_params["countTotal"]).lower()

        formatted_endpoint_url = self.endpoint_url

        response = execute_RESTful_query(
            endpoint_url=formatted_endpoint_url, variables=api_params
        )

        # Feature-14C-02: this tool always applies a hardcoded phase>=2
        # filter (see default_params_not_shown above), which silently
        # excludes every NA-phase/observational study -- the exact bucket
        # most genetics/epidemiology trials fall into. Confirmed live:
        # condition="orofacial cleft" returns total_count=0 here, but the
        # same query against the raw ClinicalTrials.gov v2 API (no phase
        # filter) surfaces real matches such as NCT03065686 ("Genetic
        # Factors Implicated in Orofacial Cleft"), which is phase "NA".
        # A bare total_count=0 is indistinguishable from "no matching
        # trials exist at all", so note the filter whenever it produced
        # zero results.
        phase_filter_applied = "PHASE2" in str(api_params.get("filter.advanced", ""))
        phase_filter_note = (
            "This search excludes phase-1-only, phase-NA, and observational "
            "studies by default (see tool description). If you expected "
            "results (e.g. for a genetics/epidemiology trial), the true "
            "match count on ClinicalTrials.gov may be higher than 0 -- "
            "consider searching https://clinicaltrials.gov/ directly for "
            "NA-phase/observational studies."
        )
        # Fix-R23-5: this note used to be attached only when the filter
        # produced zero results, so a caller who got a healthy-looking list
        # never learned that phase-1 and observational studies had been
        # dropped from it -- exactly the studies a landscape scan must not
        # miss. A non-empty result is just as filtered as an empty one, so
        # disclose the filter whenever it was applied.
        nonempty_phase_filter_note = (
            "Results exclude phase-1-only, phase-NA, and observational studies "
            "(this tool filters to phase 2/3/4 by default), so this is not the "
            "complete set of matching trials on ClinicalTrials.gov. Use "
            "ClinicalTrials_search_studies for an unfiltered search."
        )

        # Feature-27A-2: once the intervention query is restricted to the
        # registered name fields (above), a brand name that no registrant
        # recorded in either field returns zero with nothing to explain it --
        # confirmed live: query.intr=(AREA[InterventionName]Luxturna OR
        # AREA[InterventionOtherName]Luxturna) has totalCount 0, while
        # intervention="voretigene neparvovec" (the INN for the same product)
        # returns a full set. A clinician searching the name printed on the
        # vial must not read that zero as "no trials exist". This is a
        # different cause of zero from the phase gate above, so it is reported
        # as its own note and only when the restriction was actually applied.
        intervention_restricted = any(
            rw["api_field"] == "query.intr" for rw in query_rewrites
        )
        intervention_restriction_note = (
            "This search matched the intervention names and synonyms "
            "registered on each study (ClinicalTrials.gov "
            "InterventionName/InterventionOtherName), not free text in study "
            "summaries. Brand/trade names are often not recorded in either "
            "field, so if you searched one, retry with the generic/INN name "
            "(e.g. 'voretigene neparvovec' rather than 'Luxturna')."
        )

        # Fix-Round3-002: a well-formed query that legitimately matches zero
        # trials (empty `studies` list) is a success, not the error below --
        # `execute_RESTful_query` already returns False for genuine failures
        # (HTTP error, JSON decode error, API error field), so only that (or
        # a response missing "studies" entirely) is a real error.
        # _simplify_output handles an empty list fine on its own.
        if response is not None and response and "studies" in response.keys():
            metadata = {"source": "ClinicalTrials.gov API v2"}
            # Both causes of an empty result can hold at once, so name each
            # one that actually applied rather than blaming a single filter.
            notes = []
            if not response.get("studies"):
                if intervention_restricted:
                    notes.append(intervention_restriction_note)
                if phase_filter_applied:
                    notes.append(phase_filter_note)
            elif phase_filter_applied:
                notes.append(nonempty_phase_filter_note)
            if notes:
                metadata["note"] = " ".join(notes)

            # Feature-R33-1: disclose what actually ran. The notes above name
            # the *causes* of an empty result; these name the query itself, so
            # "what I asked" and "what ran" can be compared directly.
            result_data = self._attach_disclosure(
                self._simplify_output(response), api_params, query_rewrites
            )
            return {
                "status": "success",
                "data": result_data,
                "metadata": metadata,
            }

        error_msg = (
            "No studies found for the given query parameters. "
            "Please examine your input and try different parameters."
        )
        if phase_filter_applied:
            error_msg += " " + phase_filter_note
        return {
            "status": "error",
            "error": error_msg,
        }

    def _simplify_output(self, response):
        new_response = []

        for study in response["studies"]:
            new_study = {
                "NCT ID": study["protocolSection"]["identificationModule"].get("nctId"),
            }
            if "identificationModule" in study["protocolSection"]:
                new_study["brief_title"] = study["protocolSection"][
                    "identificationModule"
                ].get("briefTitle")
            if "descriptionModule" in study["protocolSection"]:
                new_study["brief_summary"] = study["protocolSection"][
                    "descriptionModule"
                ].get("briefSummary")
            if "statusModule" in study["protocolSection"]:
                new_study["overall_status"] = study["protocolSection"][
                    "statusModule"
                ].get("overallStatus")
            if "conditionsModule" in study["protocolSection"]:
                new_study["condition"] = study["protocolSection"][
                    "conditionsModule"
                ].get("conditions")
            if "designModule" in study["protocolSection"]:
                new_study["phase"] = study["protocolSection"]["designModule"].get(
                    "phases"
                )
            new_study = {
                k: v for k, v in new_study.items() if v is not None
            }  # Remove None values
            new_response.append(new_study)

        # def remove_empty_values(obj):
        #     if isinstance(obj, dict):
        #         return {k: remove_empty_values(v) for k, v in obj.items()
        #                 if v not in [0, [], None]}
        #     elif isinstance(obj, list):
        #         return [remove_empty_values(v) for v in obj if v not in [0, [], None]]
        #     else:
        #         return obj
        # new_response = remove_empty_values(new_response)

        new_response = {"studies": new_response}
        if "nextPageToken" in response:
            new_response["nextPageToken"] = response["nextPageToken"]
        if "totalCount" in response:
            new_response["total_count"] = response["totalCount"]

        return new_response


@register_tool("ClinicalTrialsDetailsTool")
class ClinicalTrialsDetailsTool(ClinicalTrialsTool):
    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.default_params_not_shown = {
            "format": "json",
        }

    def run(self, arguments):
        arguments = self._map_param_names(arguments)
        expected_param_names = self._map_param_names(self.parameters).keys()
        query_params = deepcopy(self.query_schema)

        nct_ids_list = arguments.get("nct_ids")
        if (
            not nct_ids_list
            or not isinstance(nct_ids_list, list)
            or len(nct_ids_list) == 0
        ):
            return {
                "status": "error",
                "error": "Missing or invalid required parameter: nct_ids (must be a non-empty list)",
            }
        del arguments[
            "nct_ids"
        ]  # Remove 'nct_ids' from query_params as it is not a valid API parameter

        # Prepare API parameters from arguments
        for k in expected_param_names:
            if k in arguments and arguments[k] is not None:
                query_params[k] = arguments[k]

        # Add default parameters that are not shown in the schema
        for k, v in self.default_params_not_shown.items():
            if k not in query_params:
                query_params[k] = v

        if "description_type" in expected_param_names:
            query_type = "description"
            if query_params["description_type"].lower() == "full":
                query_params["fields"] = [
                    "NCTId",
                    "BriefTitle",
                    "OfficialTitle",
                    "BriefSummary",
                    "DetailedDescription",
                    "Phase",
                ]
            else:
                query_params["fields"] = [
                    "NCTId",
                    "BriefTitle",
                    "BriefSummary",
                    "Phase",
                ]
            del query_params["description_type"]
        elif "status_and_date" in expected_param_names:
            query_type = "status_and_date"
            if "status_and_date" in query_params:
                del query_params["status_and_date"]
            query_params["fields"] = [
                "NCTId",
                "OverallStatus",
                "LastKnownStatus",
                "WhyStopped",
                "StartDate",
                "PrimaryCompletionDate",
                "CompletionDate",
            ]
        elif "condition_and_intervention" in expected_param_names:
            query_type = "condition_and_intervention"
            if "condition_and_intervention" in query_params:
                del query_params["condition_and_intervention"]
            query_params["fields"] = [
                "NCTId",
                "Condition",
                "ArmGroupLabel",
                "ArmGroupType",
                "ArmGroupDescription",
                "ArmGroupInterventionName",
                "InterventionType",
                "InterventionName",
                "InterventionOtherName",
                "InterventionDescription",
                # "InterventionArmGroupLabel",
            ]
        elif "eligibility_criteria" in expected_param_names:
            query_type = "eligibility_criteria"
            if "eligibility_criteria" in query_params:
                del query_params["eligibility_criteria"]
            query_params["fields"] = [
                "NCTId",
                "HealthyVolunteers",
                "Sex",
                "GenderBased",
                "GenderDescription",
                "MinimumAge",
                "MaximumAge",
                "StudyPopulation",
                "EligibilityCriteria",
                # "SamplingMethod",
            ]
        elif "location" in expected_param_names:
            query_type = "location"
            if "location" in query_params:
                del query_params["location"]
            query_params["fields"] = [
                "NCTId",
                "LocationFacility",
                "LocationStatus",
                "LocationCity",
                "LocationState",
                "LocationCountry",
            ]
        elif "outcome_measures" in expected_param_names:
            query_type = "outcome_measures"
            if query_params["outcome_measures"].lower() == "primary":
                query_params["fields"] = [
                    "NCTId",
                    "PrimaryOutcome",
                ]
            elif query_params["outcome_measures"].lower() == "secondary":
                query_params["fields"] = [
                    "NCTId",
                    "SecondaryOutcome",
                ]
            else:
                query_params["fields"] = [
                    "NCTId",
                    "PrimaryOutcome",
                    "SecondaryOutcome",
                    # "OtherOutcome",
                ]
            del query_params["outcome_measures"]
        elif "references" in expected_param_names:
            query_type = "references"
            if "references" in query_params:
                del query_params["references"]
            query_params["fields"] = [
                "NCTId",
                "Reference",
                "SeeAlsoLink",
            ]

        # more difficult extractions here
        elif "baseline_characteristics" in expected_param_names:
            query_type = "baseline_characteristics"
            del query_params["baseline_characteristics"]
            query_params["fields"] = [
                "NCTId",
                "BaselineCharacteristicsModule",
            ]
            # TODO: Add this to the schema

        elif "outcome_measure" in expected_param_names:
            query_type = "outcome"
            outcome_measure = query_params["outcome_measure"]
            del query_params["outcome_measure"]
            query_params["fields"] = [
                "NCTId",
                "OutcomeMeasure",
            ]

        elif "adverse_event_type" in expected_param_names:
            query_type = "safety"
            organs = query_params.get("organ_systems", [])
            adverse_event_type = query_params.get("adverse_event_type", "serious")
            if "organ_systems" in query_params:
                del query_params["organ_systems"]
            del query_params["adverse_event_type"]
            query_params["fields"] = [
                "NCTId",
                "AdverseEventsModule",
            ]

        api_params = self._prepare_api_params(query_params)
        formatted_endpoint_url = self.endpoint_url

        responses = []
        # Fix-R23-4: execute_RESTful_query returns a falsy value for every kind
        # of failure -- HTTP error, timeout, undecodable JSON -- and each of
        # those was dropped here without a trace. A transient upstream blip
        # therefore surfaced as either a short result set (some IDs silently
        # missing) or the "No relevant information found" message below, which
        # reads as "this trial has no eligibility criteria" for a trial that
        # demonstrably has them. Fetch failures and genuinely-absent data are
        # different answers and must not share a response.
        failed_ids = []
        for nct_id in nct_ids_list:
            formatted_endpoint_url = self._format_endpoint_url({"nctId": nct_id})
            response = execute_RESTful_query(
                endpoint_url=formatted_endpoint_url, variables=api_params
            )
            if response:
                responses.append(response)
            else:
                failed_ids.append(nct_id)

        if query_type not in {"outcome", "safety"}:
            responses = [
                self._simplify_output(response, query_type) for response in responses
            ]
        elif query_type == "outcome":
            responses = [
                self._extract_outcomes_from_output(response, outcome_measure)
                for response in responses
            ]
        elif query_type == "safety":
            responses = [
                self._extract_safety_from_output(response, organs, adverse_event_type)
                for response in responses
            ]

        # Fix-Round3-005: same conflation as Fix-Round3-002 (search), just in
        # this tool's detail-lookup path -- checking whether every
        # *simplified* response still had more than the bare NCT ID field
        # meant "fetched fine but this field (e.g. adverse events) is
        # legitimately empty for every trial" was indistinguishable from
        # "none of the NCT IDs could be fetched at all". `responses` here
        # is a 1:1 map over whatever was actually fetched (the list
        # comprehensions above never filter), so its emptiness is the real
        # failure signal; a request that fetched real trials but simply
        # found no matching field data for them is a legitimate success.
        if not responses:
            if failed_ids:
                return {
                    "status": "error",
                    "error": (
                        "Could not retrieve any of the requested studies from "
                        f"ClinicalTrials.gov: {', '.join(failed_ids)}. This is a "
                        "fetch failure (network error, timeout, or an "
                        "unparseable API response), not a statement that these "
                        "trials lack the requested data. Verify the NCT IDs and "
                        "retry."
                    ),
                }
            return {
                "status": "error",
                "error": "No relevant information found for the given NCT IDs.",
            }

        result = {"status": "success", "data": responses}
        if failed_ids:
            result["metadata"] = {
                "failed_nct_ids": failed_ids,
                "note": (
                    f"{len(failed_ids)} of {len(nct_ids_list)} requested studies "
                    f"could not be retrieved ({', '.join(failed_ids)}) and are "
                    "absent from `data`. These were fetch failures, not trials "
                    "lacking the requested data -- retry them before concluding "
                    "anything about them."
                ),
            }
        return result

    def _simplify_output(self, study, query_type):
        """Manually extract generally most useful information"""
        new_study = {
            "NCT ID": study["protocolSection"]["identificationModule"].get("nctId"),
        }
        if "identificationModule" in study["protocolSection"]:
            if "briefTitle" in study["protocolSection"]["identificationModule"]:
                new_study["brief_title"] = study["protocolSection"][
                    "identificationModule"
                ].get("briefTitle")
            if "officialTitle" in study["protocolSection"]["identificationModule"]:
                new_study["official_title"] = study["protocolSection"][
                    "identificationModule"
                ].get("officialTitle")
        if "statusModule" in study["protocolSection"]:
            if "overallStatus" in study["protocolSection"]["statusModule"]:
                new_study["overall_status"] = study["protocolSection"][
                    "statusModule"
                ].get("overallStatus")
            if "lastKnownStatus" in study["protocolSection"]["statusModule"]:
                new_study["last_known_status"] = study["protocolSection"][
                    "statusModule"
                ].get("lastKnownStatus")
            if "whyStopped" in study["protocolSection"]["statusModule"]:
                new_study["why_stopped"] = study["protocolSection"]["statusModule"].get(
                    "whyStopped"
                )
            if "startDateStruct" in study["protocolSection"]["statusModule"]:
                new_study["start_date"] = study["protocolSection"]["statusModule"][
                    "startDateStruct"
                ].get("date")
            if (
                "primaryCompletionDateStruct"
                in study["protocolSection"]["statusModule"]
            ):
                new_study["primary_completion_date"] = study["protocolSection"][
                    "statusModule"
                ]["primaryCompletionDateStruct"].get("date")
            if "completionDateStruct" in study["protocolSection"]["statusModule"]:
                new_study["completion_date"] = study["protocolSection"]["statusModule"][
                    "completionDateStruct"
                ].get("date")
        if "descriptionModule" in study["protocolSection"]:
            if "briefSummary" in study["protocolSection"]["descriptionModule"]:
                new_study["brief_summary"] = study["protocolSection"][
                    "descriptionModule"
                ].get("briefSummary")
            if "detailedDescription" in study["protocolSection"]["descriptionModule"]:
                new_study["detailed_description"] = study["protocolSection"][
                    "descriptionModule"
                ].get("detailedDescription")
        if "conditionsModule" in study["protocolSection"]:
            if "conditions" in study["protocolSection"]["conditionsModule"]:
                new_study["condition"] = study["protocolSection"][
                    "conditionsModule"
                ].get("conditions")
        if "designModule" in study["protocolSection"]:
            if "phases" in study["protocolSection"]["designModule"]:
                new_study["phase"] = study["protocolSection"]["designModule"].get(
                    "phases"
                )
            if "patientRegistry" in study["protocolSection"]["designModule"]:
                new_study["patient_registry"] = study["protocolSection"][
                    "designModule"
                ].get("patientRegistry")
            if "enrollmentInfo" in study["protocolSection"]["designModule"]:
                new_study["enrollment_info"] = study["protocolSection"][
                    "designModule"
                ].get("enrollmentInfo")
        if "armsInterventionsModule" in study["protocolSection"]:
            if "armGroups" in study["protocolSection"]["armsInterventionsModule"]:
                new_study["arm_groups"] = study["protocolSection"][
                    "armsInterventionsModule"
                ].get("armGroups")
            if "interventions" in study["protocolSection"]["armsInterventionsModule"]:
                new_study["interventions"] = study["protocolSection"][
                    "armsInterventionsModule"
                ].get("interventions")
        if "outcomesModule" in study["protocolSection"]:
            if "primaryOutcomes" in study["protocolSection"]["outcomesModule"]:
                new_study["primary_outcomes"] = study["protocolSection"][
                    "outcomesModule"
                ].get("primaryOutcomes")
            if "secondaryOutcomes" in study["protocolSection"]["outcomesModule"]:
                new_study["secondary_outcomes"] = study["protocolSection"][
                    "outcomesModule"
                ].get("secondaryOutcomes")
            # if "otherOutcomes" in study["protocolSection"]["outcomesModule"]:
            #     new_study["other_outcomes"] = study["protocolSection"]["outcomesModule"].get("otherOutcomes")
        if "eligibilityModule" in study["protocolSection"]:
            if "eligibilityCriteria" in study["protocolSection"]["eligibilityModule"]:
                new_study["eligibility_criteria"] = study["protocolSection"][
                    "eligibilityModule"
                ].get("eligibilityCriteria")
            if "healthyVolunteers" in study["protocolSection"]["eligibilityModule"]:
                new_study["healthy_volunteers"] = study["protocolSection"][
                    "eligibilityModule"
                ].get("healthyVolunteers")
            if "sex" in study["protocolSection"]["eligibilityModule"]:
                new_study["sex"] = study["protocolSection"]["eligibilityModule"].get(
                    "sex"
                )
            if "genderBased" in study["protocolSection"]["eligibilityModule"]:
                new_study["gender_based"] = study["protocolSection"][
                    "eligibilityModule"
                ].get("genderBased")
            if "genderDescription" in study["protocolSection"]["eligibilityModule"]:
                new_study["gender_description"] = study["protocolSection"][
                    "eligibilityModule"
                ].get("genderDescription")
            if "minimumAge" in study["protocolSection"]["eligibilityModule"]:
                new_study["minimum_age"] = study["protocolSection"][
                    "eligibilityModule"
                ].get("minimumAge")
            if "maximumAge" in study["protocolSection"]["eligibilityModule"]:
                new_study["maximum_age"] = study["protocolSection"][
                    "eligibilityModule"
                ].get("maximumAge")
            if "studyPopulation" in study["protocolSection"]["eligibilityModule"]:
                new_study["study_population"] = study["protocolSection"][
                    "eligibilityModule"
                ].get("studyPopulation")
            # if "samplingMethod" in study["protocolSection"]["eligibilityModule"]:
            #     new_study["sampling_method"] = study["protocolSection"]["eligibilityModule"].get("samplingMethod")
        if "contactsLocationsModule" in study["protocolSection"]:
            if "locations" in study["protocolSection"]["contactsLocationsModule"]:
                new_study["locations"] = study["protocolSection"][
                    "contactsLocationsModule"
                ].get("locations")
        if "referencesModule" in study["protocolSection"]:
            if "references" in study["protocolSection"]["referencesModule"]:
                new_study["references"] = study["protocolSection"][
                    "referencesModule"
                ].get("references")
            if "seeAlsoLinks" in study["protocolSection"]["referencesModule"]:
                new_study["see_also_links"] = study["protocolSection"][
                    "referencesModule"
                ].get("seeAlsoLinks")

        new_study = self._remove_empty_values(new_study)

        return new_study

    def _extract_outcomes_from_output(self, study, outcome_measure):
        new_study = {}
        outcome_measure = outcome_measure.lower()
        new_study["NCT ID"] = study["protocolSection"]["identificationModule"].get(
            "nctId"
        )

        if (
            "resultsSection" in study
            and "outcomeMeasuresModule" in study["resultsSection"]
            and "outcomeMeasures" in study["resultsSection"]["outcomeMeasuresModule"]
        ):
            raw_outcomes = study["resultsSection"]["outcomeMeasuresModule"][
                "outcomeMeasures"
            ]
            outcomes = []
            for outcome in raw_outcomes:
                new_outcome = {}

                if (outcome_measure == "primary") and outcome.get("type") != "PRIMARY":
                    continue
                if (outcome_measure == "secondary") and outcome.get(
                    "type"
                ) != "SECONDARY":
                    continue
                if (outcome_measure == "all") and outcome.get("type") not in [
                    "PRIMARY",
                    "SECONDARY",
                ]:
                    continue
                if outcome_measure not in ["primary", "secondary", "all"]:
                    outcome_measure_variants = [outcome_measure]
                    # TODO: Add more rules here
                    outcome_measure_variants.append(outcome_measure.replace("-", " "))
                    outcome_measure_variants.append(outcome_measure.replace(" ", "-"))
                    outcome_measure_variants.append(
                        outcome_measure.replace("progression", "progress")
                    )
                    outcome_measure_variants.append(
                        outcome_measure.replace("progress ", "progression ")
                    )
                    outcome_measure_variants.append(
                        outcome_measure.replace("progress-", "progression-")
                    )
                    outcome_measure_variants.append(
                        outcome_measure.replace("patient", "participant")
                    )
                    outcome_measure_variants.append(
                        outcome_measure.replace("participant", "patient")
                    )
                    outcome_measure_variants.append(outcome_measure.replace("_", " "))
                    outcome_measure_variants.append(
                        outcome_measure.replace("percentage", "percent")
                    )
                    outcome_measure_variants.append(
                        outcome_measure.replace("percent ", "percentage ")
                    )
                    outcome_measure_variants.append(
                        outcome_measure.replace("percent-", "percentage-")
                    )
                    outcome_measure_variants.append(
                        outcome_measure.replace("proportion", "percentage")
                    )
                    outcome_measure_variants.append(
                        outcome_measure.replace("percentage", "proportion")
                    )
                    outcome_measure_variants.append(
                        outcome_measure.replace("proportion", "percent")
                    )
                    outcome_measure_variants.append(
                        outcome_measure.replace("percent", "proportion")
                    )
                    outcome_measure_variants.append(
                        outcome_measure.replace("time to event", "time-to-event")
                    )
                    outcome_measure_variants.append(
                        outcome_measure.replace("time-to-event", "time to event")
                    )
                    outcome_measure_variants = list(set(outcome_measure_variants))
                    found_match = False
                    for o in outcome_measure_variants:
                        if (
                            o in outcome.get("title", "").lower()
                            or o in outcome.get("description", "").lower()
                        ):
                            found_match = True
                            break
                    if not found_match:
                        continue

                new_outcome["title"] = outcome.get("title")
                new_outcome["description"] = outcome.get("description")
                new_outcome["population"] = outcome.get("populationDescription")
                new_outcome["time_frame"] = outcome.get("timeFrame")
                new_outcome["unit_analyzed"] = outcome.get("typeUnitsAnalyzed")

                measurement_type = outcome.get("paramType")
                if measurement_type:
                    measurement_type = measurement_type.lower()
                # GEOMETRIC_MEAN - Geometric Mean
                # GEOMETRIC_LEAST_SQUARES_MEAN - Geometric Least Squares Mean
                # LEAST_SQUARES_MEAN - Least Squares Mean
                # LOG_MEAN - Log Mean
                # MEAN - Mean
                # MEDIAN - Median
                # NUMBER - Number
                # COUNT_OF_PARTICIPANTS - Count of Participants
                # COUNT_OF_UNITS - Count of Units

                unit = outcome.get("unitOfMeasure")

                new_outcome["groups"] = outcome.get("groups")

                denoms = outcome.get("denoms")
                if denoms is not None:
                    if len(denoms) > 1:
                        # TODO: Investigate such trials
                        return f"Warning: Multiple denoms found for outcome {new_outcome['title']} in study {new_study['NCT ID']}."
                    denoms = denoms[0]["counts"]
                    new_outcome["denominators"] = denoms

                classes = outcome.get("classes")
                if classes is not None:
                    if len(classes) > 1:
                        # TODO: Investigate such trials
                        return f"Warning: Multiple classes found for outcome {new_outcome['title']} in study {new_study['NCT ID']}."
                    if "title" in classes[0] or "denoms" in classes[0]:
                        # TODO: Investigate such trials
                        return f"Warning: Unexpected structure in classes for outcome {new_outcome['title']} in study {new_study['NCT ID']}."
                        classes = classes[0]
                    elif "categories" in classes[0]:
                        classes = classes[0]["categories"]
                        if len(classes) > 1:
                            # TODO: Investigate such trials
                            return f"Warning: Multiple classes-categories found for outcome {new_outcome['title']} in study {new_study['NCT ID']}."
                        if "title" in classes[0]:
                            # TODO: Investigate such trials
                            return f"Warning: Unexpected structure in classes-categories for outcome {new_outcome['title']} in study {new_study['NCT ID']}."
                            classes = classes[0]
                        elif "measurements" in classes[0]:
                            classes = classes[0]["measurements"]
                        else:
                            # TODO: Investigate such trials
                            return f"Warning: Unexpected structure in classes-categories for outcome {new_outcome['title']} in study {new_study['NCT ID']}."
                    else:
                        # TODO: Investigate such trials
                        return f"Warning: Unexpected structure in classes for outcome {new_outcome['title']} in study {new_study['NCT ID']}."

                    if measurement_type and unit:
                        new_outcome[measurement_type + " (" + unit + ")"] = classes
                    else:
                        # TODO: Investigate such trials
                        return f"Warning: Missing paramType or unitOfMeasure for outcome {new_outcome['title']} in study {new_study['NCT ID']}."

                analyses = outcome.get("analyses")
                if analyses is not None:
                    if len(analyses) > 1:
                        # TODO: Investigate such trials
                        return f"Warning: Multiple analyses found for outcome {new_outcome['title']} in study {new_study['NCT ID']}."
                    analyses = analyses[0]
                    pvalue = analyses.get("pValue")
                    pvalue_comment = analyses.get("pValueComment")
                    statistic_test = analyses.get("statisticalMethod")
                    statistic_comment = analyses.get("statisticalComment")

                    statistic_name = analyses.get("paramType")
                    statistic = analyses.get("paramValue")
                    if statistic_name and statistic_test and statistic and pvalue:
                        new_outcome["p-value (" + statistic_test + ")"] = pvalue
                        new_outcome[statistic_name] = statistic
                    else:
                        # TODO: Investigate such trials
                        return f"Warning: Missing paramType, paramValue, statisticalMethod or pvalue for outcome {new_outcome['title']} in study {new_study['NCT ID']}."
                    if statistic_comment:
                        new_outcome["statistic_comment"] = statistic_comment
                    if pvalue_comment:
                        new_outcome["pvalue_comment"] = pvalue_comment

                    statistic_test_type = analyses.get("nonInferiorityType")
                    statistic_test_type_comment = analyses.get(
                        "nonInferiorityTypeComment"
                    )
                    if statistic_test_type and statistic_test_type_comment:
                        new_outcome["statistic_test_type"] = statistic_test_type
                        new_outcome["statistic_test_type_comment"] = (
                            statistic_test_type_comment
                        )

                outcomes.append(new_outcome)

            new_study["outcomes"] = outcomes
            new_study = self._remove_empty_values(new_study)

        return new_study

    def _extract_safety_from_output(self, study, organs, adverse_event_type):
        new_study = {}
        adverse_event_type = adverse_event_type.lower()
        organs = [org.lower() for org in organs]
        new_study["NCT ID"] = study["protocolSection"]["identificationModule"].get(
            "nctId"
        )

        if (
            "resultsSection" in study
            and "adverseEventsModule" in study["resultsSection"]
        ):
            ae_data = study["resultsSection"]["adverseEventsModule"]
            new_study["freq_threshold"] = (
                ae_data["frequencyThreshold"] + "%"
                if "frequencyThreshold" in ae_data
                else None
            )
            groups = ae_data["eventGroups"]
            for group in groups:
                if "deathsNumAffected" in group:
                    del group["deathsNumAffected"]
                if "deathsNumAtRisk" in group:
                    del group["deathsNumAtRisk"]
            #     if "seriousNumAffected" in group:
            #         del group["seriousNumAffected"]
            #     if "seriousNumAtRisk" in group:
            #         del group["seriousNumAtRisk"]
            #     if "otherNumAffected" in group:
            #         del group["otherNumAffected"]
            #     if "otherNumAtRisk" in group:
            #         del group["otherNumAtRisk"]

            new_study["groups"] = groups

            if "seriousEvents" in ae_data and adverse_event_type != "other":
                raw_aes = ae_data["seriousEvents"]
                serious_aes = []
                for ae in raw_aes:
                    if adverse_event_type not in {"serious", "all"}:
                        ae_name = ae.get("term", "").lower()
                        if adverse_event_type not in ae_name:
                            continue
                    if len(organs) > 0:
                        organ_system = ae.get("organSystem", "").lower()
                        if organ_system not in organs:
                            continue

                    if "sourceVocabulary" in ae:
                        del ae["sourceVocabulary"]
                    if "assessmentType" in ae:
                        del ae["assessmentType"]

                    if "stats" in ae and len(ae["stats"]) > 0:
                        for group_stats in ae["stats"]:
                            if (
                                group_stats.get("numAffected") is not None
                                and group_stats.get("numAtRisk") is not None
                                and group_stats.get("numAtRisk", 0) > 0
                            ):
                                group_stats["percentage"] = (
                                    str(
                                        round(
                                            group_stats.get("numAffected", 0)
                                            / group_stats.get("numAtRisk", 1)
                                            * 100,
                                            2,
                                        )
                                    )
                                    + "%"
                                )
                            elif (
                                group_stats.get("numEvents") is not None
                                and group_stats.get("numAtRisk") is not None
                                and group_stats.get("numAtRisk", 0) > 0
                            ):
                                group_stats["percentage"] = (
                                    str(
                                        round(
                                            group_stats.get("numEvents", 0)
                                            / group_stats.get("numAtRisk", 1)
                                            * 100,
                                            2,
                                        )
                                    )
                                    + "%"
                                )
                            else:
                                group_stats["percentage"] = None

                            if "numEvents" in group_stats:
                                del group_stats["numEvents"]

                    serious_aes.append(ae)

                new_study["serious_adverse_events"] = serious_aes

            if "otherEvents" in ae_data and adverse_event_type != "serious":
                raw_aes = ae_data["otherEvents"]
                other_aes = []
                for ae in raw_aes:
                    if adverse_event_type not in {"other", "all"}:
                        ae_name = ae.get("term", "").lower()
                        if adverse_event_type not in ae_name:
                            continue
                    if len(organs) > 0:
                        organ_system = ae.get("organSystem", "").lower()
                        if organ_system not in organs:
                            continue

                    if "sourceVocabulary" in ae:
                        del ae["sourceVocabulary"]
                    if "assessmentType" in ae:
                        del ae["assessmentType"]

                    if "stats" in ae and len(ae["stats"]) > 0:
                        for group_stats in ae["stats"]:
                            if (
                                group_stats.get("numAffected") is not None
                                and group_stats.get("numAtRisk") is not None
                                and group_stats.get("numAtRisk", 0) > 0
                            ):
                                group_stats["percentage"] = (
                                    str(
                                        round(
                                            group_stats.get("numAffected", 0)
                                            / group_stats.get("numAtRisk", 1)
                                            * 100,
                                            2,
                                        )
                                    )
                                    + "%"
                                )
                            elif (
                                group_stats.get("numEvents") is not None
                                and group_stats.get("numAtRisk") is not None
                                and group_stats.get("numAtRisk", 0) > 0
                            ):
                                group_stats["percentage"] = (
                                    str(
                                        round(
                                            group_stats.get("numeEvents", 0)
                                            / group_stats.get("numAtRisk", 1)
                                            * 100,
                                            2,
                                        )
                                    )
                                    + "%"
                                )
                            else:
                                group_stats["percentage"] = None

                            if "numEvents" in group_stats:
                                del group_stats["numEvents"]

                    other_aes.append(ae)

                new_study["other_adverse_events"] = other_aes

            new_study = self._remove_empty_values(new_study)

        return new_study

    def _remove_empty_values(self, obj):
        if isinstance(obj, dict):
            return {
                k: self._remove_empty_values(v)
                for k, v in obj.items()
                if v not in [[], None]
            }
        elif isinstance(obj, list):
            return [self._remove_empty_values(v) for v in obj if v not in [[], None]]
        else:
            return obj
