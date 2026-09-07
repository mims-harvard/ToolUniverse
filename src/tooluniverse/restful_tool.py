from .graphql_tool import GraphQLTool, remove_none_and_empty_values
import re
import requests
import copy
from .exceptions import ToolValidationError
from .tool_registry import register_tool

_UNDERSCORE_CURIE_RE = re.compile(r"^([A-Za-z]+)_(\d+)$")


def _normalize_curie(value):
    """Convert an underscore ontology CURIE ('HP_0000639', 'MONDO_0008765') to
    the colon form Monarch requires ('HP:0000639'). OpenTargets phenotype/disease
    tools emit the underscore form, but Monarch's /entity/{id} 404s on it and
    returns "Entity not found" wrapped in status:success -- a silent false-empty
    that breaks the OpenTargets -> Monarch phenotype chain. Non-CURIE values
    (search terms, colon CURIEs) pass through unchanged."""
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    m = _UNDERSCORE_CURIE_RE.match(stripped)
    return f"{m.group(1)}:{m.group(2)}" if m else stripped


# Monarch's API rejects limit > 500 with HTTP 422 (verified live against
# https://api-v3.monarchinitiative.org/v3/api/search?q=seizure&limit=501).
_MONARCH_MAX_LIMIT = 500
# Page budget per phenotype when intersecting multiple phenotypes. 20 pages
# covers 10,000 associations -- comfortably above the most heavily annotated
# HPO terms (Seizure, the largest seen, has 5331).
_MONARCH_MAX_PAGES = 20


def _validation_error_detail(payload):
    """Return an upstream FastAPI 422 body's messages, or None.

    ``execute_RESTful_query`` hands back whatever JSON came off the wire
    regardless of HTTP status, and a FastAPI validation body carries "detail"
    rather than "error" -- so it sailed past the "error" check and was wrapped
    as a successful result. A caller branching on status then consumed the
    validation payload as if it were data.
    """
    if not isinstance(payload, dict):
        return None
    detail = payload.get("detail")
    if not detail or set(payload) - {"detail"}:
        return None
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        messages = [
            str(item.get("msg"))
            for item in detail
            if isinstance(item, dict) and item.get("msg")
        ]
        if messages:
            return "; ".join(messages)
    return None


def _tool_error(error):
    """Wrap a ToolError in the dual-format envelope callers branch on."""
    return {
        "status": "error",
        "error": str(error),
        "error_details": error.to_dict(),
    }


def _limit_error(requested_limit):
    return _tool_error(
        ToolValidationError(
            f"'limit' must be between 1 and {_MONARCH_MAX_LIMIT}; got "
            f"{requested_limit}. This tool over-fetches to survive client-side "
            "namespace filtering, so it cannot serve a larger page than the "
            "upstream API allows. Page with 'offset' to go further.",
            details={"requested_limit": requested_limit, "max": _MONARCH_MAX_LIMIT},
        )
    )


def _http_failure_reason(response, body):
    """ "HTTP <code>" plus as much of the body as is worth carrying."""
    detail = f"HTTP {response.status_code}"
    body = (body or "")[:2000].strip()
    return f"{detail}: {body[:400]}" if body else detail


def execute_RESTful_query_detailed(endpoint_url, variables=None):
    """Run the request and return ``(result, failure_reason)``.

    Fix-R48: the boolean-returning wrapper below collapses every failure mode
    into ``False`` and prints the reason to stdout, where no caller can reach
    it. Callers then had to describe a failure they could not see, and the
    honest upstream answer was thrown away. Measured live 2026-08-13:

        search_clinical_trials {"intervention": "[177Lu]Lu-PSMA-617"}
          -> "No studies found for the given query parameters. Please examine
              your input and try different parameters. This search excludes
              phase-1-only, phase-NA, and observational studies by default..."

    while ClinicalTrials.gov itself answers HTTP 400 with a precise diagnosis:

        Error parsing query in Other terms: extraneous input '[' expecting ...

    The bracketed form is standard EANM/IUPAC radiopharmaceutical nomenclature
    and appears in trial titles the tool itself returns, so it is a natural
    query rather than a malformed one. Dropping the brackets returns
    total_count 46. A caller was told zero trials exist, and told to blame the
    phase filter, for a query the API had refused to run at all.

    ``raise_for_status`` is deliberately not called: ClinicalTrials.gov puts
    its parse diagnostics in the body of the 400, so the status code alone is
    strictly less informative than what is being returned here.

    A decodable body is ALWAYS handed back, whatever the status code. That is
    not an oversight: `_validation_error_detail` above turns a FastAPI 422
    body into an actionable message, and Monarch's over-limit path depends on
    receiving that body rather than a bare failure. The first version of this
    function short-circuited on `status_code >= 400` before that check and
    crashed `MonarchTool.run` with "argument of type 'bool' is not iterable";
    a status-only rule is exactly the loss of information this function exists
    to stop. The status code is therefore consulted only when there is no body
    to read -- which is the ClinicalTrials.gov case above, whose 400 carries
    plain text rather than JSON.

    Network-level exceptions propagate, as they always have, so callers that
    rely on `requests` raising keep doing so.
    """
    response = requests.get(endpoint_url, params=variables)

    try:
        result = response.json()
        if "error" in result:
            return False, f"the API reported: {result['error']}"
        return result, None
    except requests.exceptions.JSONDecodeError:
        if response.status_code >= 400:
            return False, _http_failure_reason(response, response.text)
        return False, "the response was not valid JSON"
    except Exception as e:
        return False, str(e)


def execute_RESTful_query(endpoint_url, variables=None):
    """Backwards-compatible wrapper: the result, or ``False`` on any failure.

    Kept exactly as it was for the many callers that only branch on
    truthiness. New code that needs to tell failure modes apart should call
    ``execute_RESTful_query_detailed``.
    """
    result, reason = execute_RESTful_query_detailed(endpoint_url, variables)
    if reason is not None:
        print(f"Query failed: {reason}")
    return result


@register_tool("RESTfulTool")
class RESTfulTool(GraphQLTool):
    def __init__(self, tool_config, endpoint_url):
        super().__init__(tool_config, endpoint_url)

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)
        return execute_RESTful_query(
            endpoint_url=self.endpoint_url, variables=arguments
        )


@register_tool("Monarch")
class MonarchTool(RESTfulTool):
    def __init__(self, tool_config):
        endpoint_url = (
            "https://api.monarchinitiative.org/v3/api" + tool_config["tool_url"]
        )
        super().__init__(tool_config, endpoint_url)

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)
        query_schema_runtime = copy.deepcopy(self.query_schema)
        for key in query_schema_runtime:
            if key in arguments:
                query_schema_runtime[key] = arguments[key]

        # Feature-14C-03: the /association endpoint's "subject"/"object"
        # filters are CURIEs (e.g. "HGNC:11998"), never free-text gene/
        # disease names -- but Monarch's API doesn't reject a bare symbol
        # like "IRF6", it just matches nothing and returns an empty,
        # status:success "total": 0 page that looks identical to a real
        # "no associations for this gene" result. Confirmed live:
        # Monarch_get_gene_diseases({"subject": "IRF6"}) silently returned
        # total=0, while the correct CURIE HGNC:6121 returns 2 real
        # associations. Only checked for params whose own schema
        # description says "CURIE" (e.g. Monarch_get_gene_diseases,
        # Monarch_get_gene_phenotypes) so tools where subject/object mean
        # something else (e.g. free-text search) are unaffected.
        properties = self.tool_config.get("parameter", {}).get("properties", {})
        for curie_param in ("subject", "object"):
            value = query_schema_runtime.get(curie_param)
            if not isinstance(value, str) or not value.strip():
                continue
            description = properties.get(curie_param, {}).get("description", "")
            if "CURIE" not in description:
                continue
            if ":" not in _normalize_curie(value):
                return {
                    "status": "error",
                    "error": (
                        f"'{value}' is not a CURIE for the '{curie_param}' "
                        f"parameter. This tool requires a prefixed identifier "
                        f"like 'HGNC:11998', not a plain gene/disease name. "
                        f"Use Monarch_search_gene (or the relevant lookup "
                        f"tool) to resolve '{value}' to its CURIE first."
                    ),
                }

        if "url_key" in query_schema_runtime:
            url_key_name = query_schema_runtime["url_key"]
            # Normalize an underscore ontology CURIE (HP_0000639) to the colon
            # form Monarch's /entity/{id} needs; otherwise it 404s and returns
            # "Entity not found" as a silent status:success false-empty.
            formatted_endpoint_url = self.endpoint_url.format(
                url_key=_normalize_curie(query_schema_runtime[url_key_name])
            )
            del query_schema_runtime["url_key"]
        else:
            formatted_endpoint_url = self.endpoint_url
        if isinstance(query_schema_runtime, dict):
            if "query" in query_schema_runtime:
                query_schema_runtime["q"] = query_schema_runtime[
                    "query"
                ]  # match with the api
        result_id_prefix = self.tool_config.get("result_id_prefix")
        requested_limit = query_schema_runtime.get("limit")
        if result_id_prefix and isinstance(requested_limit, int):
            # Over-fetch since client-side filtering below removes
            # cross-ontology matches; still truncated back to
            # requested_limit after filtering so the returned count
            # matches what the caller asked for.
            #
            # Clamp to Monarch's own ceiling. Unclamped, the x3 turned any
            # requested limit above 166 into limit=501+, which Monarch rejects
            # with HTTP 422; that validation body was then returned to the
            # caller as status:"success" quoting an "input" value of 501 that
            # the caller never supplied -- an internal over-fetch factor
            # leaking out as if it were the user's own argument.
            #
            # A limit this tool cannot satisfy is an error, not a short answer.
            # Clamping alone made get_HPO_ID_by_phenotype return 490 of a
            # requested 600 under status:"success" with no note, while its
            # sibling Monarch_search_gene -- same class, no result_id_prefix,
            # so no clamp -- errored on the same request. Two tools sharing one
            # class must not answer the same over-limit call with opposite
            # contracts.
            if requested_limit > _MONARCH_MAX_LIMIT or requested_limit < 1:
                return _limit_error(requested_limit)
            query_schema_runtime["limit"] = min(requested_limit * 3, _MONARCH_MAX_LIMIT)
        response = execute_RESTful_query(
            endpoint_url=formatted_endpoint_url, variables=query_schema_runtime
        )
        if "facet_fields" in response:
            del response["facet_fields"]

        response = remove_none_and_empty_values(response)
        # Fix-R16A-2: Monarch's search endpoint has no server-side namespace
        # filter (confirmed live: a "prefix" query param is silently
        # ignored) and its "category" filter (e.g. biolink:PhenotypicFeature)
        # matches equivalent terms across multiple ontologies (HP, MP,
        # UPHENO, ...) -- so a tool promising a specific ontology's IDs (like
        # get_HPO_ID_by_phenotype) could return a non-HPO term as its
        # top-ranked hit. Opt-in, config-driven client-side filter: a tool
        # config may declare `result_id_prefix` to restrict returned items
        # to IDs starting with that prefix, without hardcoding any ontology
        # into this shared class used by other Monarch tools. Combined with
        # the over-fetch above, the returned count usually matches what the
        # caller asked for -- but when the over-fetch pool is itself capped at
        # _MONARCH_MAX_LIMIT, filtering can leave fewer. Say so rather than
        # letting a short page pass for a complete one.
        short_note = None
        if (
            result_id_prefix
            and isinstance(response, dict)
            and isinstance(response.get("items"), list)
        ):
            fetched = len(response["items"])
            filtered = [
                item
                for item in response["items"]
                if isinstance(item, dict)
                and str(item.get("id", "")).startswith(result_id_prefix)
            ]
            if isinstance(requested_limit, int):
                if len(
                    filtered
                ) < requested_limit and fetched >= query_schema_runtime.get("limit", 0):
                    short_note = (
                        f"Returned {len(filtered)} of the {requested_limit} "
                        f"requested. This tool fetches a wider page and keeps "
                        f"only '{result_id_prefix}' identifiers; the fetch hit "
                        f"the upstream ceiling of {_MONARCH_MAX_LIMIT}, so more "
                        "matches may exist. Page with 'offset' to see them."
                    )
                filtered = filtered[:requested_limit]
            response["items"] = filtered
        validation_detail = _validation_error_detail(response)
        if validation_detail:
            error = ToolValidationError(
                f"Upstream rejected the request: {validation_detail}. "
                f"This tool requests up to {_MONARCH_MAX_LIMIT} records per "
                "call; lower 'limit' or page with 'offset'.",
                # Only the upstream messages, never the raw body. The body
                # echoes the value that was actually sent, and this tool sends
                # an internally-inflated limit -- a caller who asked for 167
                # was shown "input": "501". Nothing the caller did not supply
                # should come back to them as though they had.
                details={"upstream_messages": validation_detail},
            )
            return _tool_error(error)
        if isinstance(response, dict) and "status" not in response:
            result = {"status": "success", "data": response}
            if short_note:
                result["note"] = short_note
            return result
        return response


@register_tool("MonarchDiseasesForMultiplePheno")
class MonarchDiseasesForMultiplePhenoTool(MonarchTool):
    def __init__(self, tool_config):
        super().__init__(tool_config)

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)
        query_schema_runtime = copy.deepcopy(self.query_schema)
        for key in query_schema_runtime:
            if (key != "HPO_ID_list") and (key in arguments):
                query_schema_runtime[key] = arguments[key]
        all_diseases = []
        uninformative_ids = []
        truncated_ids = []
        running = None
        # 'offset' skips entries in the returned differential. The per-leg
        # pager below drives its own offset, so leaving the caller's value in
        # the leg query made it a silent no-op: offset=0 and offset=1 returned
        # byte-identical lists. Take it out of the leg query and apply it to
        # the intersection, which is what the parameter documents.
        result_offset = query_schema_runtime.pop("offset", 0)
        result_offset = result_offset if isinstance(result_offset, int) else 0
        for HPOID in arguments["HPO_ID_list"]:
            each_query_schema_runtime = copy.deepcopy(query_schema_runtime)
            each_query_schema_runtime["object"] = HPOID
            # One page of 500 was ANDed into the intersection as if it were the
            # phenotype's whole disease set. HP:0001250 (Seizure) has 5331
            # associations upstream, so the leg carried 9% of its diseases and
            # the intersection dropped every disease outside that slice --
            # Seizure + Cataplexy lost Niemann-Pick type C, the one treatable
            # secondary cataplexy. Page through instead, and say so when the
            # budget still runs out rather than returning a short list that
            # looks definitive.
            each_output_names = []
            offset, total = 0, None
            for _ in range(_MONARCH_MAX_PAGES):
                each_query_schema_runtime["limit"] = _MONARCH_MAX_LIMIT
                each_query_schema_runtime["offset"] = offset
                page = execute_RESTful_query(
                    endpoint_url=self.endpoint_url,
                    variables=each_query_schema_runtime,
                )
                if not isinstance(page, dict):
                    break
                items = page.get("items") or []
                each_output_names.extend(
                    disease["subject_label"]
                    for disease in items
                    if isinstance(disease, dict) and disease.get("subject_label")
                )
                total = page.get("total", total)
                offset += _MONARCH_MAX_LIMIT
                if len(items) < _MONARCH_MAX_LIMIT or (
                    isinstance(total, int) and offset >= total
                ):
                    break
            if isinstance(total, int) and len(each_output_names) < total:
                truncated_ids.append(f"{HPOID} ({len(each_output_names)} of {total})")
            # Fix-R8B-9: A single unrecognized/obsolete HPO ID (typo, stale ID)
            # returns zero diseases from Monarch. Previously that empty set
            # was ANDed into the running intersection, silently collapsing
            # the WHOLE result to [] with no signal that one input ID was
            # the culprit -- a real clinician entering a mostly-correct HPO
            # panel would see "no candidate diseases" instead of a partial,
            # still-useful differential. Track zero-hit IDs separately and
            # exclude them from the intersection instead of letting them
            # veto every other (valid) phenotype in the panel.
            if each_output_names:
                all_diseases.append(each_output_names)
                # Once the running intersection is empty no later phenotype can
                # refill it, and each extra leg costs up to _MONARCH_MAX_PAGES
                # upstream requests. Stop paging phenotypes we cannot use.
                names = set(each_output_names)
                running = names if running is None else running & names
                if not running:
                    break
            else:
                uninformative_ids.append(HPOID)

        if not all_diseases:
            # Every HPO ID returned zero diseases -- genuinely no data,
            # not a single bad ID nuking a good intersection.
            return []

        # Intersect in the first phenotype's upstream (relevance-ranked) order.
        # Slicing an unordered set to `limit` made the tool nondeterministic:
        # three identical calls for HP:0002524 returned three different
        # 5-disease differentials, so whether Niemann-Pick type C appeared at
        # all depended on the process hash seed.
        other_sets = [set(element) for element in all_diseases[1:]]
        seen = set()
        intersection = []
        for name in all_diseases[0]:
            if name in seen or not all(name in other for other in other_sets):
                continue
            seen.add(name)
            intersection.append(name)
        matched_total = len(intersection)
        limit = query_schema_runtime.get("limit")
        end = result_offset + limit if isinstance(limit, int) else None
        intersection = intersection[result_offset:end]

        warnings = []
        if uninformative_ids:
            warnings.append(
                f"No disease associations found for HPO ID(s) "
                f"{uninformative_ids} (invalid/obsolete ID or a phenotype "
                "with no known disease association) -- excluded from the "
                "intersection below, which is based only on the "
                f"remaining {len(all_diseases)} of "
                f"{len(arguments['HPO_ID_list'])} input HPO ID(s)."
            )
        if truncated_ids:
            warnings.append(
                f"Disease associations were truncated for HPO ID(s) "
                f"{truncated_ids}, so this intersection may omit diseases that "
                "do carry every requested phenotype. Treat it as a partial "
                "differential, not an exhaustive one."
            )
        if warnings or matched_total > len(intersection):
            result = {"diseases": intersection, "total_matched": matched_total}
            if warnings:
                result["warning"] = " ".join(warnings)
            return result
        return intersection
