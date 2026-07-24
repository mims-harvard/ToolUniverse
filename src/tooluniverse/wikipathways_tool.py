"""WikiPathways tools — queries the WikiPathways SPARQL endpoint.

WikiPathways' legacy webservice.wikipathways.org REST API was deprecated
when the site moved to a static front-end + RDF backend. The current
public access path is the SPARQL endpoint at sparql.wikipathways.org,
which exposes the same pathway / gene / metabolite data via biolink-ish
RDF terms. We query it for both 'search by text' and 'get pathway
details' so callers see the same envelope as before.
"""

import json
from typing import Any, Dict
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tooluniverse.tool_registry import register_tool

SPARQL_ENDPOINT = "https://sparql.wikipathways.org/sparql"
_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 ToolUniverse/WikiPathways"
)


def _sparql(query: str, timeout: int = 30) -> Dict[str, Any]:
    """POST a SPARQL query to the endpoint and parse the JSON-results envelope."""
    body = urlencode({"query": query, "format": "json"}).encode()
    req = Request(
        SPARQL_ENDPOINT,
        data=body,
        method="POST",
        headers={
            "User-Agent": _BROWSER_UA,
            "Accept": "application/sparql-results+json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def _val(binding: Dict[str, Any], key: str) -> str:
    """Pull the .value field out of a SPARQL binding row, or empty string."""
    return (binding.get(key) or {}).get("value", "")


def _wpid_from_uri(uri: str) -> str:
    """https://identifiers.org/wikipathways/WP254_r140926 -> WP254."""
    tail = uri.rstrip("/").rsplit("/", 1)[-1]
    return tail.split("_", 1)[0]


@register_tool(
    "WikiPathwaysSearchTool",
    config={
        "name": "WikiPathways_search",
        "type": "WikiPathwaysSearchTool",
        "description": (
            "Search WikiPathways for pathways by free-text title match. "
            "Returns WPIDs, titles, and organisms. Backed by the "
            "sparql.wikipathways.org SPARQL endpoint."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Text to search, e.g., p53"},
                "organism": {
                    "type": "string",
                    "description": "Optional organism filter, e.g., 'Homo sapiens'",
                },
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["query"],
        },
        "settings": {"timeout": 30},
    },
)
class WikiPathwaysSearchTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]):
        timeout = int((self.tool_config.get("settings") or {}).get("timeout", 30))
        query = (arguments.get("query") or "").lower().replace('"', "")
        organism = arguments.get("organism")
        limit = int(arguments.get("limit", 20))

        organism_filter = (
            f'  FILTER(LCASE(STR(?organism)) = "{organism.lower()}")'
            if organism
            else ""
        )
        sparql = f"""
PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
SELECT DISTINCT ?pathway ?title ?organism WHERE {{
  ?pathway a wp:Pathway ;
           dc:title ?title ;
           wp:organismName ?organism .
  FILTER(CONTAINS(LCASE(?title), "{query}"))
{organism_filter}
}} LIMIT {limit}
"""
        try:
            j = _sparql(sparql, timeout=timeout)
        except Exception as e:
            return {"status": "error", "error": f"WikiPathways SPARQL error: {e}"}

        results = [
            {
                "wpid": _wpid_from_uri(_val(b, "pathway")),
                "uri": _val(b, "pathway"),
                "title": _val(b, "title"),
                "organism": _val(b, "organism"),
            }
            for b in j.get("results", {}).get("bindings", [])
        ]
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "query": query,
                "count": len(results),
                "backend": "WikiPathways SPARQL",
            },
        }


@register_tool(
    "WikiPathwaysGetTool",
    config={
        "name": "WikiPathways_get_pathway",
        "type": "WikiPathwaysGetTool",
        "description": (
            "Fetch a WikiPathways pathway by WPID. Returns title, organism, "
            "description, and the list of gene / metabolite participants. "
            "Backed by the sparql.wikipathways.org SPARQL endpoint."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "wpid": {"type": "string", "description": "Pathway ID, e.g., WP254"},
            },
            "required": ["wpid"],
        },
        "settings": {"timeout": 30},
    },
)
class WikiPathwaysGetTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]):
        timeout = int((self.tool_config.get("settings") or {}).get("timeout", 30))
        wpid = (arguments.get("wpid") or "").upper().replace('"', "")
        if not wpid:
            return {"status": "error", "error": "wpid parameter is required"}

        # The pathway URI ends with /<WPID>_r<revision>, and dc:identifier
        # is the un-revisioned identifiers.org URI. Filter on the URI pattern.
        identifier_uri = f"https://identifiers.org/wikipathways/{wpid}"
        info_sparql = f"""
PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX dcterms: <http://purl.org/dc/terms/>
SELECT ?pathway ?title ?organism WHERE {{
  ?pathway a wp:Pathway ;
           dc:identifier <{identifier_uri}> ;
           dc:title ?title ;
           wp:organismName ?organism .
}} LIMIT 1
"""
        gene_sparql = f"""
PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?gene_id ?gene_label ?datasource WHERE {{
  ?gene dcterms:isPartOf ?pathway ;
        a wp:GeneProduct ;
        dc:identifier ?gene_id ;
        rdfs:label ?gene_label ;
        dc:source ?datasource .
  ?pathway dc:identifier <{identifier_uri}> .
}} LIMIT 200
"""
        try:
            info = _sparql(info_sparql, timeout=timeout)
            genes = _sparql(gene_sparql, timeout=timeout)
        except Exception as e:
            return {"status": "error", "error": f"WikiPathways SPARQL error: {e}"}

        bindings = info.get("results", {}).get("bindings", [])
        if not bindings:
            return {
                "status": "error",
                "error": f"Pathway '{wpid}' not found in WikiPathways SPARQL endpoint",
            }
        b = bindings[0]
        gene_list = [
            {
                "id": _val(g, "gene_id"),
                "label": _val(g, "gene_label"),
                "datasource": _val(g, "datasource"),
            }
            for g in genes.get("results", {}).get("bindings", [])
        ]
        return {
            "status": "success",
            "data": {
                "wpid": wpid,
                "uri": _val(b, "pathway"),
                "title": _val(b, "title"),
                "organism": _val(b, "organism"),
                "genes": gene_list,
                "gene_count": len(gene_list),
            },
            "metadata": {"backend": "WikiPathways SPARQL"},
        }
