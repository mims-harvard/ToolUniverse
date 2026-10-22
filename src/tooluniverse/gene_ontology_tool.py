import requests
from typing import Any, Dict, Optional
from urllib.parse import quote
from .base_tool import BaseTool
from .tool_registry import register_tool

# Defaults applied to GOlr URL templates when the caller omits the parameter.
_GOLR_TEMPLATE_DEFAULTS = {"rows": 100, "start": 0}


def _drop_unfilled_query_segments(url: str) -> str:
    """Remove query segments still holding an unsubstituted {placeholder}.

    An optional filter the caller omitted must not be sent as the literal
    string "{taxon}" -- Solr would then match nothing and the tool would report
    an empty result set as though the term genuinely had no genes.
    """
    if "{" not in url or "?" not in url:
        return url
    base, _, query = url.partition("?")
    kept = [
        segment
        for segment in query.split("&")
        if not ("{" in segment and "}" in segment)
    ]
    return f"{base}?{'&'.join(kept)}" if kept else base


@register_tool("GeneOntologyTool")
class GeneOntologyTool(BaseTool):
    """
    A general-purpose tool for calling the Gene Ontology (GO) API.
    It is configured via a dictionary that defines the specific API endpoint.
    """

    def __init__(self, tool_config: Dict):
        """
        Initializes the tool with a configuration.

        Args:
            tool_config (Dict): A dictionary containing 'fields' with an 'endpoint'.
        """
        super().__init__(tool_config)
        self.endpoint = tool_config["fields"]["endpoint"]
        self.extract_path = tool_config["fields"].get("extract_path")
        self.timeout = 20

    def _build_url(self, args: Dict[str, Any]) -> str:
        """Builds the request URL from arguments."""
        url = self.endpoint
        for key, value in args.items():
            url = url.replace(f"{{{key}}}", quote(str(value)))
        return url

    def _extract_data(self, data: Dict, extract_path: str) -> Any:
        """Extract specific data from the GO API response using custom paths."""

        if extract_path == "response.docs[0]":
            # Extract single document from GOlr response
            response = data.get("response", {})
            docs = response.get("docs", [])
            if docs:
                return docs[0]
            else:
                return {"status": "error", "error": "No GO term found"}

        elif extract_path == "response.docs":
            # Extract all documents from GOlr response
            response = data.get("response", {})
            docs = response.get("docs", [])
            return docs

        elif extract_path == "response.docs.genes":
            # Collapse GOlr annotation rows into distinct genes. GOlr returns one
            # row per annotation, so a gene backed by several evidence codes
            # appears many times; counting rows would overstate the gene count.
            response = data.get("response", {})
            docs = response.get("docs", [])
            genes = {}
            for doc in docs:
                bioentity = doc.get("bioentity")
                if not bioentity:
                    continue
                gene = genes.setdefault(
                    bioentity,
                    {
                        "bioentity": bioentity,
                        "gene_symbol": doc.get("bioentity_label"),
                        "gene_name": doc.get("bioentity_name"),
                        "taxon": doc.get("taxon"),
                        "taxon_label": doc.get("taxon_label"),
                        "evidence_types": [],
                        "annotation_count": 0,
                    },
                )
                gene["annotation_count"] += 1
                evidence = doc.get("evidence_type")
                if evidence and evidence not in gene["evidence_types"]:
                    gene["evidence_types"].append(evidence)
            return list(genes.values())

        # For simple paths, try direct access
        try:
            if "." in extract_path:
                keys = extract_path.split(".")
                result = data
                for key in keys:
                    if "[" in key and "]" in key:
                        # Handle array indexing like "docs[0]"
                        array_key = key.split("[")[0]
                        index_str = key.split("[")[1].split("]")[0]
                        result = result.get(array_key, [])
                        if index_str.isdigit():
                            index = int(index_str)
                            if index < len(result):
                                result = result[index]
                            else:
                                return {
                                    "status": "error",
                                    "error": f"Index {index} out of range",
                                }
                        else:
                            return {
                                "status": "error",
                                "error": f"Invalid array index: {index_str}",
                            }
                    else:
                        result = result.get(key, {})
                return result
            else:
                return data.get(extract_path)
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to extract data using path '{extract_path}': {e}",
            }

    def run(self, arguments: Any = None) -> Any:
        """
        Executes the API call and returns the data.

        Args:
            arguments (Dict[str, Any]): Parameters for the API call.

        Returns
            Any: The JSON data from the API or an error dictionary.
        """
        # Normalize arguments
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            return {
                "status": "error",
                "error": "Invalid arguments type; expected a mapping/dict.",
            }

        pagination_mode = self.tool_config.get("fields", {}).get("pagination")
        if pagination_mode == "golr_start":
            rows = arguments.get("rows", _GOLR_TEMPLATE_DEFAULTS["rows"])
            start = arguments.get("start", _GOLR_TEMPLATE_DEFAULTS["start"])
            if (
                not isinstance(rows, int)
                or isinstance(rows, bool)
                or not 1 <= rows <= 1000
            ):
                return {
                    "status": "error",
                    "error": "rows must be an integer between 1 and 1000.",
                }
            if not isinstance(start, int) or isinstance(start, bool) or start < 0:
                return {
                    "status": "error",
                    "error": "start must be a non-negative integer.",
                }
            arguments = dict(arguments)
            arguments["rows"] = rows
            arguments["start"] = start

        # Handle different endpoint formats
        if "?" in self.endpoint:
            # This is a complete URL with query parameters (GOlr format)
            url = self.endpoint
            template_args = dict(arguments)
            for key, default in _GOLR_TEMPLATE_DEFAULTS.items():
                if f"{{{key}}}" in url and key not in template_args:
                    template_args[key] = default
            for key, value in template_args.items():
                url = url.replace(f"{{{key}}}", quote(str(value)))
            url = _drop_unfilled_query_segments(url)
            params = {}
        else:
            # This is a template URL (Biolink format)
            url_args = arguments.copy()
            params = {}

            # Move query parameters to params dict for Biolink API
            if "taxon" in arguments:
                params["taxon"] = url_args.pop("taxon")
            if "rows" in arguments:
                params["rows"] = url_args.pop("rows")
            if "start" in arguments:
                params["start"] = url_args.pop("start")

            # Build URL with remaining arguments
            url = self._build_url(url_args)

        try:
            resp = requests.get(
                url,
                params=params,
                timeout=self.timeout,
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {
                    "status": "error",
                    "error": "The requested resource was not found (404 Not Found).",
                }
            return {
                "status": "error",
                "error": f"GO API request failed with HTTP status: {e.response.status_code}",
                "detail": e.response.text,
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"A network error occurred while requesting the GO API: {e}",
            }
        except ValueError:
            return {
                "status": "error",
                "error": "Failed to parse GO API response, which may not be valid JSON.",
                "content": resp.text,
            }

        # If extract_path is configured, extract the corresponding subset
        if self.extract_path:
            result = self._extract_data(data, self.extract_path)

            if pagination_mode == "golr_start":
                response = data.get("response", {})
                docs = response.get("docs", [])
                total_rows = response.get("numFound")
                response_start = response.get("start", arguments["start"])
                returned_rows = len(docs) if isinstance(docs, list) else 0
                has_more = (
                    isinstance(total_rows, int)
                    and response_start + returned_rows < total_rows
                )
                result_unit = self.tool_config["fields"].get(
                    "pagination_result_unit", "annotations"
                )
                returned = len(result) if isinstance(result, list) else 1
                rows_are_results = result_unit != "distinct_genes"
                metadata = {
                    "returned": returned,
                    "returned_rows": returned_rows,
                    "total_rows": total_rows,
                    "rows_total_is_exact": isinstance(total_rows, int),
                    "total_results": total_rows if rows_are_results else None,
                    "total_results_is_exact": (
                        isinstance(total_rows, int) if rows_are_results else False
                    ),
                    "result_unit": result_unit,
                    "start": response_start,
                    "rows": arguments["rows"],
                    "has_more": has_more,
                    "next_start": (
                        response_start + returned_rows if has_more else None
                    ),
                    "truncated": has_more,
                    "result_set_complete": not has_more and response_start == 0,
                    "pagination_scope": self.tool_config["fields"].get(
                        "pagination_scope", "GOlr result rows"
                    ),
                }
                if result_unit in {"annotations", "distinct_genes"}:
                    metadata.update(
                        {
                            "returned_annotation_rows": returned_rows,
                            "total_annotation_rows": total_rows,
                            "annotation_rows_total_is_exact": isinstance(
                                total_rows, int
                            ),
                        }
                    )
                return {"status": "success", "data": result, "metadata": metadata}

            # Handle empty results
            if isinstance(result, list) and len(result) == 0:
                return {
                    "status": "error",
                    "error": f"No data found for path: {self.extract_path}",
                }
            elif isinstance(result, dict) and "error" in result:
                return result

            return result

        return data

    # Method bindings for backward compatibility and convenience
    def search_terms(self, query: str) -> Any:
        return self.run({"query": query})

    def get_term_details(self, id: str) -> Any:
        return self.run({"id": id})

    def get_genes_for_term(
        self,
        id: str,
        taxon: Optional[str] = None,
        rows: Optional[int] = None,
        start: Optional[int] = None,
    ) -> Any:
        args = {"id": id}
        if taxon:
            args["taxon"] = taxon
        if rows:
            args["rows"] = rows
        if start is not None:
            args["start"] = start
        return self.run(args)

    def get_terms_for_gene(self, id: str) -> Any:
        return self.run({"id": id})
