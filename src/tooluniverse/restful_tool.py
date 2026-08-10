from .graphql_tool import GraphQLTool, remove_none_and_empty_values
import re
import requests
import copy
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


def execute_RESTful_query(endpoint_url, variables=None):
    response = requests.get(endpoint_url, params=variables)
    try:
        result = response.json()

        if "error" in result:
            print("Invalid Query: ", result["error"])
            return False
        return result
    except requests.exceptions.JSONDecodeError:
        print("JSONDecodeError: Could not decode the response as JSON")
        return False
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred: {e}")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False


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
            query_schema_runtime["limit"] = requested_limit * 3
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
        # the over-fetch above, the returned count still matches what the
        # caller asked for.
        if (
            result_id_prefix
            and isinstance(response, dict)
            and isinstance(response.get("items"), list)
        ):
            filtered = [
                item
                for item in response["items"]
                if isinstance(item, dict)
                and str(item.get("id", "")).startswith(result_id_prefix)
            ]
            if isinstance(requested_limit, int):
                filtered = filtered[:requested_limit]
            response["items"] = filtered
        if isinstance(response, dict) and "status" not in response:
            return {"status": "success", "data": response}
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
        for HPOID in arguments["HPO_ID_list"]:
            each_query_schema_runtime = copy.deepcopy(query_schema_runtime)
            each_query_schema_runtime["object"] = HPOID
            each_query_schema_runtime["limit"] = 500
            each_output = execute_RESTful_query(
                endpoint_url=self.endpoint_url, variables=each_query_schema_runtime
            )
            each_output = each_output["items"]
            each_output_names = [disease["subject_label"] for disease in each_output]
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
            else:
                uninformative_ids.append(HPOID)

        if not all_diseases:
            # Every HPO ID returned zero diseases -- genuinely no data,
            # not a single bad ID nuking a good intersection.
            return []

        intersection = set(all_diseases[0])
        for element in all_diseases[1:]:
            intersection &= set(element)
        intersection = list(intersection)
        if query_schema_runtime["limit"] < len(intersection):
            intersection = intersection[: query_schema_runtime["limit"]]
        if uninformative_ids:
            return {
                "diseases": intersection,
                "warning": (
                    f"No disease associations found for HPO ID(s) "
                    f"{uninformative_ids} (invalid/obsolete ID or a phenotype "
                    "with no known disease association) -- excluded from the "
                    "intersection below, which is based only on the "
                    f"remaining {len(all_diseases)} of "
                    f"{len(arguments['HPO_ID_list'])} input HPO ID(s)."
                ),
            }
        return intersection
