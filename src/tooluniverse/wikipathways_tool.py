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
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tooluniverse.tool_registry import register_tool

SPARQL_ENDPOINT = "https://sparql.wikipathways.org/sparql"
GPML_URL = (
    "https://www.wikipathways.org/wikipathways-assets/pathways/{wpid}/{wpid}.gpml"
)
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


def _fetch_gpml(wpid: str, timeout: int = 30) -> str:
    """Fetch the raw GPML XML for a pathway from the static asset host.

    WikiPathways serves each pathway's GPML at a predictable static path
    (confirmed live: WP254.gpml, 200 with ~75 KB of XML); an unknown WPID
    answers 404.
    """
    req = Request(
        GPML_URL.format(wpid=wpid),
        headers={"User-Agent": _BROWSER_UA, "Accept": "application/xml"},
    )
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def _sparql_literal(value: str) -> str:
    """Escape a Python string for interpolation inside a SPARQL string literal."""
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def _validated_int(arguments, name, default, minimum=0, maximum=None):
    value = arguments.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int):
        return None, f"{name} must be an integer"
    if value < minimum:
        return None, f"{name} must be at least {minimum}"
    if maximum is not None and value > maximum:
        return None, f"{name} must be at most {maximum}"
    return value, None


@register_tool(
    "WikiPathwaysSearchTool",
    config={
        "name": "WikiPathways_search",
        "type": "WikiPathwaysSearchTool",
        "description": (
            "Search WikiPathways for pathways by free-text title match. "
            "Returns recoverably paginated WPIDs, titles, and organisms. "
            "Continue with metadata.next_offset while metadata.has_more. "
            "Backed by the sparql.wikipathways.org SPARQL endpoint."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Text to search, e.g., p53"},
                "organism": {
                    "type": "string",
                    "description": "Optional organism filter, e.g., 'Homo sapiens'",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "default": 20,
                },
                "offset": {"type": "integer", "minimum": 0, "default": 0},
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
        raw_query = arguments.get("query")
        if not isinstance(raw_query, str) or not raw_query.strip():
            return {"status": "error", "error": "query must be a non-empty string"}
        query = raw_query.strip().lower()
        organism = arguments.get("organism")
        if organism is not None and (
            not isinstance(organism, str) or not organism.strip()
        ):
            return {
                "status": "error",
                "error": "organism must be a non-empty string",
            }
        limit, error = _validated_int(arguments, "limit", 20, 1, 200)
        if error:
            return {"status": "error", "error": error}
        offset, error = _validated_int(arguments, "offset", 0, 0)
        if error:
            return {"status": "error", "error": error}

        # Fix-11B-2: pathway titles in WikiPathways are typically unhyphenated
        # gene/protein shorthand ("IL4 signaling"), but researchers naturally
        # type the hyphenated form ("IL-4 signaling") -- confirmed live this
        # returned zero results even though the pathway exists (WP395).
        # Stripping hyphens from both sides of the CONTAINS comparison keeps
        # the plain-substring search simple while absorbing this common
        # notation mismatch.
        query_norm = _sparql_literal(query.replace("-", ""))

        organism_filter = (
            f'  FILTER(LCASE(STR(?organism)) = "{_sparql_literal(organism.strip().lower())}")'
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
  FILTER(CONTAINS(REPLACE(LCASE(?title), "-", ""), "{query_norm}"))
{organism_filter}
}}
ORDER BY LCASE(STR(?title)) STR(?pathway)
LIMIT {limit + 1}
OFFSET {offset}
"""
        try:
            j = _sparql(sparql, timeout=timeout)
        except Exception as e:
            return {"status": "error", "error": f"WikiPathways SPARQL error: {e}"}

        all_results = [
            {
                "wpid": _wpid_from_uri(_val(b, "pathway")),
                "uri": _val(b, "pathway"),
                "title": _val(b, "title"),
                "organism": _val(b, "organism"),
            }
            for b in j.get("results", {}).get("bindings", [])
        ]
        has_more = len(all_results) > limit
        results = all_results[:limit]
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "query": query,
                "returned": len(results),
                "offset": offset,
                "limit": limit,
                "has_more": has_more,
                "next_offset": offset + len(results) if has_more else None,
                "complete": not has_more,
                "total_hits": None,
                "total_hits_is_known": False,
                "backend": "WikiPathways SPARQL",
            },
        }


@register_tool(
    "WikiPathwaysGetTool",
    config={
        "name": "WikiPathways_get_pathway",
        "type": "WikiPathwaysGetTool",
        "description": (
            "Fetch a WikiPathways pathway by WPID. JSON returns metadata and "
            "recoverably paginated gene-participant rows with exact totals; "
            "GPML returns the complete official static XML asset."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "wpid": {"type": "string", "description": "Pathway ID, e.g., WP254"},
                "format": {
                    "type": "string",
                    "enum": ["json", "gpml"],
                    "default": "json",
                },
                "gene_limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "default": 200,
                },
                "gene_offset": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 0,
                },
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
        raw_wpid = arguments.get("wpid")
        if not isinstance(raw_wpid, str) or not raw_wpid.strip():
            return {"status": "error", "error": "wpid must be a non-empty string"}
        wpid = raw_wpid.strip().upper()
        if not wpid.startswith("WP") or not wpid[2:].isdigit():
            return {"status": "error", "error": "wpid must match WP followed by digits"}

        output_format = arguments.get("format") or "json"
        if output_format not in {"json", "gpml"}:
            return {"status": "error", "error": "format must be json or gpml"}
        if output_format == "gpml":
            # The "format" parameter used to be accepted but ignored: every
            # call ran the JSON/SPARQL path below regardless of the value.
            try:
                gpml = _fetch_gpml(wpid, timeout=timeout)
            except HTTPError as e:
                if e.code == 404:
                    return {
                        "status": "error",
                        "error": f"Pathway '{wpid}' has no GPML file (HTTP 404)",
                    }
                return {"status": "error", "error": f"WikiPathways GPML error: {e}"}
            except Exception as e:
                return {"status": "error", "error": f"WikiPathways GPML error: {e}"}
            return {
                "status": "success",
                "data": {
                    "wpid": wpid,
                    "format": "gpml",
                    "gpml": gpml,
                    "source_url": GPML_URL.format(wpid=wpid),
                },
                "metadata": {
                    "backend": "WikiPathways static assets",
                    "complete": True,
                },
            }

        gene_limit, error = _validated_int(arguments, "gene_limit", 200, 1, 500)
        if error:
            return {"status": "error", "error": error}
        gene_offset, error = _validated_int(arguments, "gene_offset", 0, 0)
        if error:
            return {"status": "error", "error": error}

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
}}
ORDER BY STR(?gene_id) LCASE(STR(?gene_label)) STR(?datasource)
LIMIT {gene_limit + 1}
OFFSET {gene_offset}
"""
        count_sparql = f"""
PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT (COUNT(*) AS ?total_rows) (COUNT(DISTINCT ?gene) AS ?gene_products) WHERE {{
  {{
    SELECT DISTINCT ?gene ?gene_id ?gene_label ?datasource WHERE {{
      ?gene dcterms:isPartOf ?pathway ;
            a wp:GeneProduct ;
            dc:identifier ?gene_id ;
            rdfs:label ?gene_label ;
            dc:source ?datasource .
      ?pathway dc:identifier <{identifier_uri}> .
    }}
  }}
}}
"""
        try:
            info = _sparql(info_sparql, timeout=timeout)
            genes = _sparql(gene_sparql, timeout=timeout)
            counts = _sparql(count_sparql, timeout=timeout)
        except Exception as e:
            return {"status": "error", "error": f"WikiPathways SPARQL error: {e}"}

        bindings = info.get("results", {}).get("bindings", [])
        if not bindings:
            return {
                "status": "error",
                "error": f"Pathway '{wpid}' not found in WikiPathways SPARQL endpoint",
            }
        b = bindings[0]
        all_gene_rows = [
            {
                "id": _val(g, "gene_id"),
                "label": _val(g, "gene_label"),
                "datasource": _val(g, "datasource"),
            }
            for g in genes.get("results", {}).get("bindings", [])
        ]
        count_bindings = counts.get("results", {}).get("bindings", [])
        if not count_bindings:
            return {
                "status": "error",
                "error": "WikiPathways SPARQL did not return participant counts",
            }
        try:
            total_gene_rows = int(_val(count_bindings[0], "total_rows"))
            gene_product_count = int(_val(count_bindings[0], "gene_products"))
        except (TypeError, ValueError):
            return {
                "status": "error",
                "error": "WikiPathways SPARQL returned invalid participant counts",
            }
        gene_list = all_gene_rows[:gene_limit]
        expected_more = gene_offset + len(gene_list) < total_gene_rows
        pagination_stalled = expected_more and not gene_list
        has_more = expected_more and not pagination_stalled
        return {
            "status": "success",
            "data": {
                "wpid": wpid,
                "uri": _val(b, "pathway"),
                "title": _val(b, "title"),
                "organism": _val(b, "organism"),
                "genes": gene_list,
                "gene_count": total_gene_rows,
                "gene_product_count": gene_product_count,
            },
            "metadata": {
                "backend": "WikiPathways SPARQL",
                "gene_rows_returned": len(gene_list),
                "gene_offset": gene_offset,
                "gene_limit": gene_limit,
                "total_gene_rows": total_gene_rows,
                "total_gene_rows_is_exact": True,
                "gene_product_count": gene_product_count,
                "gene_product_count_is_exact": True,
                "has_more": has_more,
                "next_gene_offset": (
                    gene_offset + len(gene_list) if has_more else None
                ),
                "pagination_stalled": pagination_stalled,
                "complete": not has_more and not pagination_stalled,
            },
        }
