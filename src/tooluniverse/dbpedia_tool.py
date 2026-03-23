"""
DBpedia tools for ToolUniverse using SPARQL endpoint.

This module provides access to DBpedia structured knowledge using SPARQL
queries. DBpedia extracts structured information from Wikipedia and makes
it available as linked data. No API key is required.
"""

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

    def run(self, arguments=None):
        arguments = arguments or {}
        sparql = arguments.get("sparql")
        max_results = arguments.get("max_results")
        if not sparql:
            return {"error": "`sparql` parameter is required."}
        if max_results:
            # naive limit appending if not present
            if "limit" not in sparql.lower():
                sparql = f"{sparql}\nLIMIT {int(max_results)}"

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
                "error": "Network/API error calling DBpedia SPARQL",
                "reason": str(e),
            }
        except ValueError:
            ct = resp.headers.get("content-type", "")
            return {
                "error": "Failed to decode SPARQL response as JSON",
                "content_type": ct,
                "response_snippet": resp.text[:200],
                "retryable": "text/html" in ct or resp.text.lstrip().startswith("<"),
                "suggestion": "DBpedia SPARQL endpoint may be under maintenance. Retry in a few minutes.",
            }

        bindings = data.get("results", {}).get("bindings", [])
        # Normalize by unwrapping "value" fields
        normalized = []
        for b in bindings:
            row = {}
            for k, v in b.items():
                row[k] = v.get("value")
            normalized.append(row)
        return normalized
