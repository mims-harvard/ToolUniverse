from graphql import build_schema
from graphql.language import parse
from graphql.validation import validate
from .base_tool import BaseTool
from .tool_registry import register_tool
import requests
import copy
import time

# Upper bound on how long DiseaseTargetScoreTool will paginate through
# OpenTargets associatedTargets before returning what it has so far. A
# disease can have >10,000 associated targets; without a bound the loop
# issues hundreds of sequential requests and can run for many minutes.
_DISEASE_TARGET_SCORE_TIME_BUDGET_S = 25.0


def validate_query(query_str, schema_str):
    try:
        # Build the GraphQL schema object from the provided schema string
        schema = build_schema(schema_str)

        # Parse the query string into an AST (Abstract Syntax Tree)
        query_ast = parse(query_str)

        # Validate the query AST against the schema
        validation_errors = validate(schema, query_ast)

        if not validation_errors:
            return True
        else:
            # Collect and return the validation errors
            error_messages = "\n".join(str(error) for error in validation_errors)
            return f"Query validation errors:\n{error_messages}"
    except Exception as e:
        return f"An error occurred during validation: {str(e)}"


def remove_none_and_empty_values(json_obj):
    """Remove all key-value pairs where the value is None or an empty list"""
    if isinstance(json_obj, dict):
        return {
            k: remove_none_and_empty_values(v)
            for k, v in json_obj.items()
            if v is not None and v != []
        }
    elif isinstance(json_obj, list):
        return [
            remove_none_and_empty_values(item)
            for item in json_obj
            if item is not None and item != []
        ]
    else:
        return json_obj


def execute_query(endpoint_url, query, variables=None):
    response = requests.post(
        endpoint_url, json={"query": query, "variables": variables}, timeout=30
    )
    try:
        if not response.ok:
            print(f"HTTP {response.status_code} from API: {response.text[:200]}")
            return None
        result = response.json()
        result = remove_none_and_empty_values(result)
        # Check if the response contains errors
        if "errors" in result:
            print("Invalid Query: ", result["errors"])
            return None
        # Feature-94A-002: always return result when data key is present,
        # even if all values are empty/null (e.g. disease not found = {"data": {}}).
        # Callers distinguish empty results from errors via status envelope.
        elif "data" not in result:
            print("No data returned")
            return None
        else:
            return result
    except requests.exceptions.JSONDecodeError:
        print("JSONDecodeError: Could not decode the response as JSON")
        return None


class GraphQLTool(BaseTool):
    def __init__(self, tool_config, endpoint_url):
        super().__init__(tool_config)
        self.endpoint_url = endpoint_url
        self.query_schema = tool_config["query_schema"]
        self.parameters = tool_config["parameter"]["properties"]
        self.default_size = 5

    def _empty_result_error(self, arguments):
        """Message when a query resolves but every top-level field is null/empty.

        Subclasses override this to give API-specific guidance (e.g. an
        EFO->MONDO hint for OpenTargets). The default names the arguments so the
        caller can see which identifier failed to resolve.
        """
        return (
            "The query returned no matching record — the requested entity was not "
            f"found. Verify the identifier(s) are current and correct: {arguments}."
        )

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)
        if "size" in self.parameters and "size" not in arguments:
            arguments["size"] = self.default_size
        result = execute_query(
            endpoint_url=self.endpoint_url, query=self.query_schema, variables=arguments
        )
        if result is None:
            return {"status": "error", "error": "No data returned from API"}
        data = result.get("data", result)
        # remove_none_and_empty_values() strips a null/empty top-level entity, so
        # data == {} means the requested record was not found. Report that
        # explicitly rather than as a misleading empty success. A genuine empty
        # *result set* (e.g. a 0-hit search) keeps its container key
        # ({"search": {}}) and is therefore not caught here.
        if not data:
            return {"status": "error", "error": self._empty_result_error(arguments)}
        return {"status": "success", "data": data}


_OT_SEARCH_QUERY = """
query otSearch($q: String!, $entity: [String!]!) {
  search(queryString: $q, entityNames: $entity, page: {index: 0, size: 1}) {
    hits { id name }
  }
}
"""


def _ot_resolve_id(endpoint_url: str, query_string: str, entity: str) -> str | None:
    """Resolve a gene symbol or disease name to an OpenTargets ID via search."""
    result = execute_query(
        endpoint_url,
        _OT_SEARCH_QUERY,
        {"q": query_string, "entity": [entity]},
    )
    if result:
        hits = result.get("data", {}).get("search", {}).get("hits", [])
        if hits:
            return hits[0]["id"]
    return None


def _ot_entity_not_found_message(arguments):
    """Build a helpful error when an OpenTargets ID does not resolve.

    OpenTargets migrated most disease IDs from EFO to MONDO, so many legacy
    EFO disease IDs (e.g. EFO_0000305 breast carcinoma) now resolve to null
    and the API returns an empty entity. Surface that explicitly instead of a
    misleading empty success (issue #264).
    """
    disease_id = arguments.get("efoId") or arguments.get("entityId")
    if isinstance(arguments.get("diseaseIds"), list) and arguments["diseaseIds"]:
        disease_id = arguments["diseaseIds"][0]
    if disease_id is not None:
        return (
            f"OpenTargets returned no disease for ID '{disease_id}'. OpenTargets "
            "migrated most disease IDs from EFO to MONDO, so many legacy EFO "
            "disease IDs now resolve to null. Pass a current MONDO ID (e.g. "
            "MONDO_0005011 for Crohn disease); look up a disease's current ID by "
            "name with OpenTargets_multi_entity_search_by_query_string."
        )
    ensembl_id = arguments.get("ensemblId")
    if ensembl_id is not None:
        return (
            f"OpenTargets returned no target for Ensembl ID '{ensembl_id}'. "
            "Verify the ID (e.g. ENSG00000141510 for TP53) or pass gene_symbol "
            "to auto-resolve it."
        )
    return (
        "OpenTargets returned no entity for the provided identifier(s). Verify "
        "the ID is current — OpenTargets periodically remaps disease IDs from "
        "EFO to MONDO."
    )


@register_tool("OpenTarget")
class OpentargetTool(GraphQLTool):
    def __init__(self, tool_config):
        self.endpoint_url = "https://api.platform.opentargets.org/api/v4/graphql"
        super().__init__(tool_config, self.endpoint_url)

    def _empty_result_error(self, arguments):
        return _ot_entity_not_found_message(arguments)

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)

        # Normalize common aliases before resolution
        if "ensemblId" not in arguments and "gene_symbol" not in arguments:
            for alias in ("target", "gene", "gene_name"):
                if arguments.get(alias):
                    arguments["gene_symbol"] = arguments.pop(alias)
                    break
        if "efoId" not in arguments and "disease_name" not in arguments:
            for alias in ("disease", "disease_id", "trait"):
                if arguments.get(alias):
                    arguments["disease_name"] = arguments.pop(alias)
                    break

        # Resolve gene_symbol → ensemblId if ensemblId not provided
        if "ensemblId" not in arguments and "gene_symbol" in arguments:
            resolved = _ot_resolve_id(
                self.endpoint_url, arguments.pop("gene_symbol"), "target"
            )
            if resolved:
                arguments["ensemblId"] = resolved
            else:
                return {
                    "status": "error",
                    "error": f"Could not resolve gene symbol to Ensembl ID. "
                    "Try passing ensemblId directly (e.g. ENSG00000141510 for TP53).",
                }

        # Resolve disease_name → efoId (or diseaseIds) if not provided
        needs_disease_ids = "diseaseIds" in self.query_schema
        if (
            "efoId" not in arguments
            and "diseaseIds" not in arguments
            and "disease_name" in arguments
        ):
            resolved = _ot_resolve_id(
                self.endpoint_url, arguments.pop("disease_name"), "disease"
            )
            if resolved:
                if needs_disease_ids:
                    arguments["diseaseIds"] = [resolved]
                else:
                    arguments["efoId"] = resolved
            else:
                return {
                    "status": "error",
                    "error": "Could not resolve disease name to a disease ID. "
                    "Try passing efoId directly (e.g. MONDO_0005011 for Crohn disease).",
                }

        result = super().run(arguments)

        # Add note when IntOGen evidence count is 0 (Feature-122B-002)
        if result.get("status") == "success":
            evidences = result.get("data", {}).get("disease", {}).get("evidences", {})
            if isinstance(evidences, dict) and evidences.get("count") == 0:
                result.setdefault("metadata", {})["note"] = (
                    "IntOGen returns 0 evidence rows for this query. "
                    "IntOGen only covers somatic tumor driver mutations — "
                    "it has no data for non-cancer diseases or non-driver genes. "
                    "For non-oncology phenotypes, use OpenTargets_get_evidence_by_datasource instead."
                )

        # If no results AND an argument contains '-', retry once with '-'
        # replaced by ' ' (rescues hyphenated names). The hyphen guard keeps a
        # genuine not-found (e.g. a stale efoId) from issuing a redundant
        # identical query.
        if result.get("status") != "success" and any(
            isinstance(v, str) and "-" in v for v in arguments.values()
        ):
            if "drugName" in arguments and isinstance(arguments["drugName"], str):
                arguments["drugName"] = arguments["drugName"].split("-")[0]
            modified_arguments = copy.deepcopy(arguments)
            for each_arg, arg_value in modified_arguments.items():
                if isinstance(arg_value, str) and "-" in arg_value:
                    modified_arguments[each_arg] = arg_value.replace("-", " ")
            result = super().run(modified_arguments)

        return result


@register_tool("OpentargetToolDrugNameMatch")
class OpentargetToolDrugNameMatch(GraphQLTool):
    def __init__(self, tool_config, drug_generic_tool=None):
        endpoint_url = "https://api.platform.opentargets.org/api/v4/graphql"
        self.drug_generic_tool = drug_generic_tool
        self.possible_drug_name_args = ["drugName"]
        super().__init__(tool_config, endpoint_url)

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)
        results = execute_query(
            endpoint_url=self.endpoint_url, query=self.query_schema, variables=arguments
        )
        if results is None:
            print(
                "No results found for the drug brand name. Trying with the generic name."
            )
            # Find which drug name argument was provided
            matched_arg = None
            for arg_name in self.possible_drug_name_args:
                if arg_name in arguments:
                    matched_arg = arg_name
                    break
            if matched_arg is None:
                print("No drug name found in the arguments.")
                return {"status": "error", "error": "No drug name found in arguments"}
            drug_name_results = self.drug_generic_tool.run(
                {"drug_name": arguments[matched_arg]}
            )
            if (
                drug_name_results is not None
                and "openfda.generic_name" in drug_name_results
            ):
                arguments[matched_arg] = drug_name_results["openfda.generic_name"]
                print(
                    "Found generic name. Trying with the generic name: ",
                    arguments[matched_arg],
                )
                results = execute_query(
                    endpoint_url=self.endpoint_url,
                    query=self.query_schema,
                    variables=arguments,
                )
        if results is None:
            return {"status": "error", "error": "No data returned from API"}
        return {"status": "success", "data": results.get("data", results)}


@register_tool("OpenTargetGenetics")
class OpentargetGeneticsTool(GraphQLTool):
    def __init__(self, tool_config):
        endpoint_url = "https://api.genetics.opentargets.org/graphql"
        super().__init__(tool_config, endpoint_url)

    def run(self, arguments):
        arguments = copy.deepcopy(arguments)
        # Resolve disease_name → diseaseIds if not already provided
        if "diseaseIds" not in arguments:
            disease_name = None
            for alias in ("disease_name", "disease", "trait"):
                if arguments.get(alias):
                    disease_name = arguments.pop(alias)
                    break
            if disease_name:
                resolved = _ot_resolve_id(
                    "https://api.platform.opentargets.org/api/v4/graphql",
                    disease_name,
                    "disease",
                )
                if resolved:
                    arguments["diseaseIds"] = [resolved]
                else:
                    return {
                        "status": "error",
                        "error": (
                            f"Could not resolve '{disease_name}' to a disease ID. "
                            "Try passing diseaseIds directly (e.g. ['MONDO_0005148'] for type 2 diabetes)."
                        ),
                    }
        return super().run(arguments)


@register_tool("DiseaseTargetScoreTool")
class DiseaseTargetScoreTool(GraphQLTool):
    """Tool to extract disease-target association scores from specific data sources"""

    def __init__(self, tool_config, datasource_id=None):
        endpoint_url = "https://api.platform.opentargets.org/api/v4/graphql"
        # Get datasource_id from config if not provided as parameter
        self.datasource_id = datasource_id or tool_config.get("datasource_id")
        super().__init__(tool_config, endpoint_url)

    def _empty_result_error(self, arguments):
        return _ot_entity_not_found_message(arguments)

    def run(self, arguments):
        """
        Extract disease-target scores for a specific datasource
        Arguments should contain: efoId, datasourceId (optional), pageSize (optional)
        """
        arguments = copy.deepcopy(arguments)
        efo_id = arguments.get("efoId")
        datasource_id = arguments.get("datasourceId", self.datasource_id)
        page_size = arguments.get("pageSize", 100)

        if not efo_id:
            return {"status": "error", "error": "efoId is required"}
        if not datasource_id:
            return {"status": "error", "error": "datasourceId is required"}

        results = []
        page_index = 0
        total_fetched = 0
        total_count = None
        disease_info = None
        truncated = False

        deadline = time.monotonic() + _DISEASE_TARGET_SCORE_TIME_BUDGET_S

        while True:
            # Bound total wall-clock time. A disease can have >10,000
            # associated targets; without this the loop can run for minutes.
            if time.monotonic() >= deadline:
                truncated = True
                break

            variables = {"efoId": efo_id, "index": page_index, "size": page_size}

            response_data = execute_query(
                self.endpoint_url, self.query_schema, variables
            )
            if not response_data or "data" not in response_data:
                break

            # remove_none_and_empty_values() drops a null "disease" key, so use
            # .get() rather than [] (a missing key would raise KeyError). When
            # the ID does not resolve on the first page, report it explicitly
            # instead of returning an empty success (issue #264).
            disease_data = response_data["data"].get("disease")
            if not disease_data:
                if disease_info is None:
                    return {
                        "status": "error",
                        "error": self._empty_result_error(arguments),
                    }
                break

            if disease_info is None:
                disease_info = {
                    "disease_id": disease_data["id"],
                    "disease_name": disease_data["name"],
                }

            rows = disease_data["associatedTargets"]["rows"]
            if total_count is None:
                total_count = disease_data["associatedTargets"]["count"]

            for row in rows:
                symbol = row["target"]["approvedSymbol"]
                target_id = row["target"]["id"]
                score_entry = next(
                    (ds for ds in row["datasourceScores"] if ds["id"] == datasource_id),
                    None,
                )
                if score_entry:
                    results.append(
                        {
                            "target_symbol": symbol,
                            "target_id": target_id,
                            "datasource": datasource_id,
                            "score": score_entry["score"],
                        }
                    )

            total_fetched += len(rows)
            if total_fetched >= total_count or len(rows) == 0:
                break
            page_index += 1

        data = {
            "disease_info": disease_info,
            "datasource": datasource_id,
            "total_targets_with_scores": len(results),
            "target_scores": results,
        }
        if truncated:
            data["truncated"] = True
            data["note"] = (
                f"Stopped after {_DISEASE_TARGET_SCORE_TIME_BUDGET_S:.0f}s; "
                f"scanned {total_fetched} of {total_count} associated targets. "
                "Increase pageSize to scan more targets per request, or query a "
                "more specific disease."
            )
        return {"status": "success", "data": data}
