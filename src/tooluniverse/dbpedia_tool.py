"""
DBpedia tools for ToolUniverse using SPARQL endpoint.

This module provides access to DBpedia structured knowledge using SPARQL
queries. DBpedia extracts structured information from Wikipedia and makes
it available as linked data. No API key is required.
"""

import re

import requests
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("DBpediaSPARQLTool")
class DBpediaSPARQLTool(BaseTool):
    """
    Run SPARQL queries against DBpedia to retrieve structured knowledge.

    DBpedia is a project that extracts structured information from Wikipedia
    and makes it available as linked data. This tool is particularly useful
    for querying information about people, places, organizations, works,
    and other entities, especially in humanities and social sciences domains.

    Parameters (arguments):
        sparql (str): SPARQL query string
        max_results (int): Optional result limit override
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = "https://dbpedia.org/sparql"

    @staticmethod
    def _query_type(sparql):
        match = re.search(r"\b(SELECT|ASK|CONSTRUCT|DESCRIBE)\b", sparql, re.I)
        return match.group(1).upper() if match else None

    @staticmethod
    def _strip_trailing_page_clauses(sparql):
        """Remove only terminal numeric LIMIT/OFFSET clauses, not subquery clauses."""
        query = sparql.strip().rstrip(";").rstrip()
        found = {}
        while True:
            match = re.search(r"(?is)\s+(LIMIT|OFFSET)\s+(\d+)\s*$", query)
            if not match:
                break
            found.setdefault(match.group(1).lower(), int(match.group(2)))
            query = query[: match.start()].rstrip()
        return query, found

    def run(self, arguments=None):
        arguments = arguments or {}
        sparql = arguments.get("sparql")
        max_results = arguments.get("max_results")
        offset = arguments.get("offset")
        if not isinstance(sparql, str) or not sparql.strip():
            return {"status": "error", "error": "`sparql` parameter is required."}
        if max_results is not None and (
            isinstance(max_results, bool)
            or not isinstance(max_results, int)
            or not 1 <= max_results <= 1000
        ):
            return {
                "status": "error",
                "error": "max_results must be an integer from 1 to 1000",
            }
        if offset is not None and (
            isinstance(offset, bool) or not isinstance(offset, int) or offset < 0
        ):
            return {
                "status": "error",
                "error": "offset must be a non-negative integer",
            }

        query_type = self._query_type(sparql)
        if query_type not in {"SELECT", "ASK"}:
            return {
                "status": "error",
                "error": (
                    "Only SELECT and ASK queries are supported because CONSTRUCT and "
                    "DESCRIBE do not return SPARQL-results JSON"
                ),
            }

        submitted_query = sparql.strip()
        effective_limit = None
        effective_offset = None
        if query_type == "SELECT":
            base_query, existing = self._strip_trailing_page_clauses(submitted_query)
            effective_limit = (
                max_results if max_results is not None else existing.get("limit", 100)
            )
            effective_offset = (
                offset if offset is not None else existing.get("offset", 0)
            )
            sparql = (
                f"{base_query}\nLIMIT {effective_limit + 1}\nOFFSET {effective_offset}"
            )
        elif max_results is not None or (offset is not None and offset != 0):
            return {
                "status": "error",
                "error": "max_results and non-zero offset apply only to SELECT queries",
            }

        headers = {
            "Accept": "application/sparql-results+json",
            "User-Agent": "ToolUniverse/1.0 (https://github.com)",
        }
        try:
            resp = requests.get(
                self.endpoint,
                params={"query": sparql, "format": "json"},
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            return {
                "status": "error",
                "error": "Network/API error calling DBpedia SPARQL",
                "reason": str(e),
            }
        except ValueError:
            ct = resp.headers.get("content-type", "")
            return {
                "status": "error",
                "error": "Failed to decode SPARQL response as JSON",
                "content_type": ct,
                "response_snippet": resp.text[:200],
                "retryable": "text/html" in ct or resp.text.lstrip().startswith("<"),
                "suggestion": "DBpedia SPARQL endpoint may be under maintenance. Retry in a few minutes.",
            }

        if not isinstance(data, dict):
            return {
                "status": "error",
                "error": "DBpedia returned a non-object JSON response",
            }
        if query_type == "ASK":
            value = data.get("boolean")
            if not isinstance(value, bool):
                return {
                    "status": "error",
                    "error": "DBpedia ASK response did not contain a boolean result",
                }
            return {
                "status": "success",
                "data": {"query_type": "ASK", "boolean": value},
                "metadata": {
                    "source": "DBpedia SPARQL",
                    "requested_scope_complete": True,
                },
            }

        results_object = data.get("results")
        bindings = (
            results_object.get("bindings") if isinstance(results_object, dict) else None
        )
        variables = (
            data.get("head", {}).get("vars")
            if isinstance(data.get("head"), dict)
            else None
        )
        if not isinstance(bindings, list) or not isinstance(variables, list):
            return {
                "status": "error",
                "error": "DBpedia SELECT response lacked head.vars or results.bindings",
            }
        if any(not isinstance(binding, dict) for binding in bindings):
            return {
                "status": "error",
                "error": "DBpedia SELECT response contained a malformed binding row",
            }

        has_more = len(bindings) > effective_limit
        page_bindings = bindings[:effective_limit]
        normalized = []
        for binding in page_bindings:
            row = {}
            for key, value in binding.items():
                if not isinstance(value, dict) or "value" not in value:
                    return {
                        "status": "error",
                        "error": "DBpedia SELECT response contained a malformed variable binding",
                    }
                row[key] = value["value"]
            normalized.append(row)

        returned = len(normalized)
        result_set_complete = not has_more
        return {
            "status": "success",
            "data": {
                "query_type": "SELECT",
                "variables": variables,
                "results": normalized,
                "bindings": page_bindings,
                "offset": effective_offset,
                "limit": effective_limit,
                "returned": returned,
                "has_more": has_more,
                "next_offset": effective_offset + returned if has_more else None,
                "result_set_complete": result_set_complete,
                "total_count": effective_offset + returned
                if result_set_complete
                else None,
            },
            "metadata": {
                "source": "DBpedia SPARQL",
                "qualifiers_preserved": True,
                "explicit_order_by": bool(
                    re.search(r"\bORDER\s+BY\b", submitted_query, re.I)
                ),
                "pagination_stability_guaranteed": False,
                "pagination_guidance": (
                    "Use SELECT DISTINCT and ORDER BY a unique key to prevent duplicate "
                    "bindings or tied sort values from overlapping adjacent offset pages."
                ),
                "requested_scope_complete": True,
            },
        }
