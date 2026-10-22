# hgnc_tool.py
"""
HGNC (HUGO Gene Nomenclature Committee) REST API tool for ToolUniverse.

HGNC is the worldwide authority that assigns standardised nomenclature to
human genes. The REST API provides access to approved gene symbols, names,
aliases, chromosomal locations, and cross-references to external databases.

API: https://rest.genenames.org/
No authentication required. Free for academic/research use.
"""

from typing import Dict, Any
from urllib.parse import quote

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

HGNC_BASE_URL = "https://rest.genenames.org"
_SEARCH_FIELDS = {
    "symbol",
    "name",
    "alias_symbol",
    "prev_symbol",
    "entrez_id",
    "ensembl_gene_id",
    "uniprot_ids",
    "location",
}


@register_tool("HGNCTool")
class HGNCTool(BaseTool):
    """
    Tool for querying the HGNC gene nomenclature database.

    HGNC provides authoritative human gene naming. Supports fetching genes by
    symbol, HGNC ID, or searching by various fields including name, location,
    and aliases.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint_type = fields.get("endpoint", "search")
        self.default_search_field = fields.get("search_field")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the HGNC API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"HGNC API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to HGNC API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"HGNC API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying HGNC: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an HGNC query and return structured results."""
        headers = {"Accept": "application/json"}

        if self.endpoint_type == "fetch":
            return self._fetch(arguments, headers)
        else:
            return self._search(arguments, headers)

    @staticmethod
    def _response_docs(data: Any) -> tuple[list, int, int, str | None]:
        if not isinstance(data, dict) or not isinstance(data.get("response"), dict):
            return [], 0, 0, "HGNC response lacked a response object"
        response = data["response"]
        docs = response.get("docs")
        num_found = response.get("numFound")
        start = response.get("start", 0)
        if not isinstance(docs, list) or any(not isinstance(doc, dict) for doc in docs):
            return [], 0, 0, "HGNC response contained malformed docs"
        if (
            isinstance(num_found, bool)
            or not isinstance(num_found, int)
            or num_found < 0
            or isinstance(start, bool)
            or not isinstance(start, int)
            or start < 0
        ):
            return [], 0, 0, "HGNC response contained invalid result counts"
        if start != 0 or len(docs) != num_found:
            return (
                docs,
                num_found,
                start,
                "HGNC returned a partial result set despite its unpaginated API contract",
            )
        return docs, num_found, start, None

    def _fetch(self, arguments: Dict[str, Any], headers: Dict) -> Dict[str, Any]:
        """Fetch a specific gene record by symbol or HGNC ID.

        For ``gene_group_id`` the fetch endpoint returns every member gene of
        the family/group, so all docs are returned as a list rather than a
        single record.
        """
        search_field = self.default_search_field

        if search_field == "symbol":
            value = arguments.get("symbol")
            if not isinstance(value, str) or not value.strip():
                return {
                    "status": "error",
                    "error": "symbol must be a non-empty string",
                }
            value = value.strip()
        elif search_field == "hgnc_id":
            value = arguments.get("hgnc_id")
            if not isinstance(value, str) or not value.strip():
                return {
                    "status": "error",
                    "error": "hgnc_id must be a non-empty string",
                }
            raw_id = value.strip()
            suffix = raw_id.split(":", 1)[1] if ":" in raw_id else raw_id
            if not suffix.isdigit():
                return {
                    "status": "error",
                    "error": "hgnc_id must contain a numeric HGNC identifier",
                }
            value = f"HGNC:{suffix}"
        elif search_field == "gene_group_id":
            value = arguments.get("gene_group_id", "")
            if isinstance(value, bool) or not isinstance(value, (str, int)):
                return {
                    "status": "error",
                    "error": "gene_group_id must be a positive integer or digit string",
                }
            value = str(value).strip()
            if not value.isdigit() or int(value) < 1:
                return {
                    "status": "error",
                    "error": "gene_group_id must be a positive integer or digit string",
                }
        else:
            return {"status": "error", "error": f"Unknown fetch field: {search_field}"}

        url = f"{HGNC_BASE_URL}/fetch/{search_field}/{quote(value, safe=':')}"
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        docs, num_found, _, response_error = self._response_docs(data)
        if response_error:
            return {
                "status": "error",
                "error": response_error,
                "returned": len(docs),
                "num_found": num_found,
            }

        # gene_group_id enumerates every member gene of a family → return all
        if search_field == "gene_group_id":
            invalid_members = [
                doc.get("hgnc_id")
                for doc in docs
                if int(value) not in doc.get("gene_group_id", [])
            ]
            if invalid_members:
                return {
                    "status": "error",
                    "error": "HGNC returned genes outside the requested gene group",
                    "invalid_members": invalid_members,
                }
            return {
                "status": "success",
                "data": docs,
                "metadata": {
                    "source": "HGNC",
                    "query_field": search_field,
                    "query_value": value,
                    "num_found": num_found,
                    "returned": len(docs),
                    "result_set_complete": True,
                },
            }

        if not docs:
            return {
                "status": "success",
                "data": {},
                "metadata": {
                    "source": "HGNC",
                    "query_field": search_field,
                    "query_value": value,
                    "num_found": 0,
                    "returned": 0,
                    "exact_identifier_verified": False,
                    "result_set_complete": True,
                },
            }

        if num_found != 1:
            return {
                "status": "error",
                "error": "HGNC exact fetch did not return one unique record",
                "num_found": num_found,
            }
        gene = docs[0]
        returned_value = gene.get(search_field)
        matches = (
            isinstance(returned_value, str) and returned_value.lower() == value.lower()
        )
        if not matches:
            return {
                "status": "error",
                "error": "HGNC exact fetch returned a different identifier",
                "requested_value": value,
                "returned_value": returned_value,
            }
        return {
            "status": "success",
            "data": gene,
            "metadata": {
                "source": "HGNC",
                "query_field": search_field,
                "query_value": value,
                "num_found": num_found,
                "returned": 1,
                "exact_identifier_verified": True,
                "result_set_complete": True,
            },
        }

    def _search(self, arguments: Dict[str, Any], headers: Dict) -> Dict[str, Any]:
        """Search for genes by various criteria."""
        search_field = arguments.get("search_field", self.default_search_field)
        if search_field is not None and (
            not isinstance(search_field, str) or search_field not in _SEARCH_FIELDS
        ):
            return {
                "status": "error",
                "error": "search_field is not a supported HGNC search field",
            }

        # Determine the query value
        argument_name = (
            "location" if self.default_search_field == "location" else "query"
        )
        query = arguments.get(argument_name)
        if not isinstance(query, str) or not query.strip():
            return {
                "status": "error",
                "error": f"{argument_name} must be a non-empty string",
            }
        query = query.strip()
        encoded_query = quote(query, safe="*")

        if search_field:
            url = f"{HGNC_BASE_URL}/search/{search_field}/{encoded_query}"
        else:
            url = f"{HGNC_BASE_URL}/search/{encoded_query}"

        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        docs, num_found, _, response_error = self._response_docs(data)
        if response_error:
            return {
                "status": "error",
                "error": response_error,
                "returned": len(docs),
                "num_found": num_found,
            }

        return {
            "status": "success",
            "data": docs,
            "metadata": {
                "source": "HGNC",
                "total_results": num_found,
                "returned": len(docs),
                "result_set_complete": True,
                "pagination_supported": False,
                "query": query,
                "query_field": search_field,
            },
        }
