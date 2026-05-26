# wikipathways_ext_tool.py
"""WikiPathways Extended tool — backed by the SPARQL endpoint.

The legacy webservice.wikipathways.org REST API (getXrefList,
findPathwaysByXref) was deprecated; this tool now talks to
sparql.wikipathways.org which is the current public access path. The
envelope shape and parameter names are unchanged.
"""

import json
from typing import Any, Dict
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .base_tool import BaseTool


SPARQL_ENDPOINT = "https://sparql.wikipathways.org/sparql"
_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 ToolUniverse/WikiPathways"
)

# Legacy single-letter codes accepted by the old getXrefList endpoint.
# Map them to the BridgeDB datasource URIs that the SPARQL store uses
# inside `dc:source`.
CODE_TO_NAME = {
    "H": "HGNC Symbol",
    "En": "Ensembl",
    "S": "UniProt",
    "L": "Entrez Gene",
    "Ce": "ChEBI",
}
# SPARQL store uses BridgeDB-style source strings; keep the friendly
# substring match flexible so we accept both URI-form and short-form sources.
_CODE_TO_SOURCE_SUBSTR = {
    "H": "HGNC",
    "En": "Ensembl",
    "S": "Uniprot",
    "L": "Entrez Gene",
    "Ce": "ChEBI",
}


def _sparql(query: str, timeout: int = 30) -> Dict[str, Any]:
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
    return (binding.get(key) or {}).get("value", "")


def _wpid_from_uri(uri: str) -> str:
    tail = uri.rstrip("/").rsplit("/", 1)[-1]
    return tail.split("_", 1)[0]


class WikiPathwaysExtTool(BaseTool):
    """WikiPathways extended endpoints via SPARQL."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_pathway_genes")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if self.endpoint == "get_pathway_genes":
                return self._get_pathway_genes(arguments)
            if self.endpoint == "find_pathways_by_gene":
                return self._find_pathways_by_gene(arguments)
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}
        except Exception as e:  # noqa: BLE001
            return {
                "status": "error",
                "error": f"Unexpected error querying WikiPathways: {e}",
            }

    def _get_pathway_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        pathway_id = (arguments.get("pathway_id") or "").upper().replace('"', "")
        if not pathway_id:
            return {
                "status": "error",
                "error": "pathway_id parameter is required (e.g., 'WP254')",
            }

        code = arguments.get("code", "H")
        id_type_name = CODE_TO_NAME.get(code, code)
        source_substr = _CODE_TO_SOURCE_SUBSTR.get(code, code)

        identifier_uri = f"https://identifiers.org/wikipathways/{pathway_id}"
        sparql = f"""
PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?gene_id ?gene_label WHERE {{
  ?gene dcterms:isPartOf ?pathway ;
        a wp:GeneProduct ;
        dc:identifier ?gene_id ;
        rdfs:label ?gene_label ;
        dc:source ?src .
  ?pathway dc:identifier <{identifier_uri}> .
  FILTER(CONTAINS(STR(?src), "{source_substr}"))
}} LIMIT 500
"""
        data = _sparql(sparql, timeout=self.timeout)
        # SPARQL returns the gene URI in ?gene_id; flatten to the bare label
        # so callers see the same {gene_count, genes:[symbol]} shape as before.
        symbols = sorted(
            {
                _val(b, "gene_label")
                for b in data.get("results", {}).get("bindings", [])
                if _val(b, "gene_label")
            }
        )
        return {
            "status": "success",
            "data": {
                "pathway_id": pathway_id,
                "gene_count": len(symbols),
                "identifier_type": id_type_name,
                "genes": symbols,
            },
            "metadata": {
                "source": "WikiPathways SPARQL",
                "pathway_id": pathway_id,
                "code": code,
            },
        }

    def _find_pathways_by_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        gene = (arguments.get("gene") or "").replace('"', "")
        if not gene:
            return {
                "status": "error",
                "error": "gene parameter is required (e.g., 'TP53', 'BRCA1')",
            }

        species = arguments.get("species", "Homo sapiens")
        organism_filter = (
            f'  FILTER(LCASE(STR(?organism)) = "{species.lower()}")' if species else ""
        )

        sparql = f"""
PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?pathway ?title ?organism WHERE {{
  ?gene dcterms:isPartOf ?pathway ;
        a wp:GeneProduct ;
        rdfs:label "{gene}" .
  ?pathway a wp:Pathway ;
           dc:title ?title ;
           wp:organismName ?organism .
{organism_filter}
}} LIMIT 100
"""
        data = _sparql(sparql, timeout=self.timeout)
        bindings = data.get("results", {}).get("bindings", [])
        seen = set()
        pathways = []
        for b in bindings:
            uri = _val(b, "pathway")
            pid = _wpid_from_uri(uri)
            if pid in seen:
                continue
            seen.add(pid)
            pathways.append(
                {
                    "id": pid,
                    "name": _val(b, "title"),
                    "species": _val(b, "organism"),
                    "url": uri,
                }
            )

        return {
            "status": "success",
            "data": {
                "gene": gene,
                "total_pathways": len(pathways),
                "pathways": pathways,
            },
            "metadata": {
                "source": "WikiPathways SPARQL",
                "gene": gene,
                "species": species,
            },
        }
