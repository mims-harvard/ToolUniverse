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


def _resolve_pathway_id(arguments: Dict[str, Any]) -> str:
    """`pathway_id`, normalized, accepting `wpid` as an alias.

    WikiPathways_get_pathway (the sibling tool in wikipathways_tool.py) names
    this parameter `wpid`; accept it here too so a caller who just used that
    tool doesn't hit a validation error switching to this one.
    """
    return (arguments.get("pathway_id") or arguments.get("wpid") or "").upper().replace(
        '"', ""
    )


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
            if self.endpoint == "get_pathway_metabolites":
                return self._get_pathway_metabolites(arguments)
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}
        except Exception as e:  # noqa: BLE001
            return {
                "status": "error",
                "error": f"Unexpected error querying WikiPathways: {e}",
            }

    def _get_pathway_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        pathway_id = _resolve_pathway_id(arguments)
        if not pathway_id:
            return {
                "status": "error",
                "error": "pathway_id parameter is required (e.g., 'WP254')",
            }

        # `code` used to default to "H" (HGNC), but WikiPathways' RDF store
        # annotates gene products with the database they were drawn from, and
        # HGNC is rare there -- WP254's 87 gene products are sourced from
        # Entrez Gene (84) and Ensembl (3), none from HGNC. The default filter
        # therefore matched nothing and the tool reported "0 genes" for its own
        # documented 88-gene example. `code` is now an optional filter.
        code = arguments.get("code")
        id_type_name = CODE_TO_NAME.get(code, code) if code else "All sources"

        source_filter = ""
        if code:
            source_substr = _CODE_TO_SOURCE_SUBSTR.get(code, code)
            # Case-insensitive: the store writes "UniProtKB", not "Uniprot".
            source_filter = (
                f'\n  FILTER(CONTAINS(LCASE(STR(?src)), "{source_substr.lower()}"))'
            )

        identifier_uri = f"https://identifiers.org/wikipathways/{pathway_id}"
        sparql = f"""
PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?gene ?gene_label WHERE {{
  ?gene dcterms:isPartOf ?pathway ;
        a wp:GeneProduct ;
        rdfs:label ?gene_label ;
        dc:source ?src .
  ?pathway dc:identifier <{identifier_uri}> .{source_filter}
}} LIMIT 2000
"""
        data = _sparql(sparql, timeout=self.timeout)
        # One gene product carries several rdfs:label aliases, so counting
        # labels overstated the gene set -- WP254 read as 134 genes against 87
        # actual gene products. Count the nodes instead. The aliases are not
        # reliable enough to pick a single symbol from (WikiPathways attaches
        # "PIK3CA" to the AKT1 node among others), so every label is reported
        # rather than one being guessed at.
        labels_by_gene: Dict[str, set] = {}
        for binding in data.get("results", {}).get("bindings", []):
            gene_uri = _val(binding, "gene")
            label = _val(binding, "gene_label")
            if not gene_uri or not label:
                continue
            labels_by_gene.setdefault(gene_uri, set()).add(label)

        symbols = sorted({lbl for labels in labels_by_gene.values() for lbl in labels})
        gene_products = [
            {"identifier": uri, "labels": sorted(labels)}
            for uri, labels in sorted(labels_by_gene.items())
        ]
        return {
            "status": "success",
            "data": {
                "pathway_id": pathway_id,
                "gene_count": len(labels_by_gene),
                "label_count": len(symbols),
                "identifier_type": id_type_name,
                "genes": symbols,
                "gene_products": gene_products,
            },
            "metadata": {
                "source": "WikiPathways SPARQL",
                "pathway_id": pathway_id,
                "code": code,
            },
        }

    def _get_pathway_metabolites(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Return the metabolite/compound participants of a WikiPathways pathway.

        Selects nodes typed `a wp:Metabolite` that are part of the given
        pathway, returning each distinct metabolite with its canonical
        identifier (HMDB / ChEBI / KEGG / etc.), its `dc:source` datasource,
        and a representative label. For a metabolic pathway these compounds are
        the central entities (unlike get_pathway_genes which returns only gene
        products).
        """
        pathway_id = _resolve_pathway_id(arguments)
        if not pathway_id:
            return {
                "status": "error",
                "error": "pathway_id parameter is required (e.g., 'WP534')",
            }

        identifier_uri = f"https://identifiers.org/wikipathways/{pathway_id}"
        sparql = f"""
PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?metabolite ?label ?identifier ?source WHERE {{
  ?metabolite dcterms:isPartOf ?pathway ;
        a wp:Metabolite ;
        rdfs:label ?label ;
        dc:identifier ?identifier ;
        dc:source ?source .
  ?pathway dc:identifier <{identifier_uri}> .
}} LIMIT 1000
"""
        data = _sparql(sparql, timeout=self.timeout)
        bindings = data.get("results", {}).get("bindings", [])

        # Collapse rows to one entry per distinct metabolite node. The SPARQL
        # store emits a separate row per rdfs:label alias; collect all aliases
        # then pick the most descriptive one (prefer a real name with a
        # lowercase letter over an all-caps abbreviation; then prefer longer).
        by_node: Dict[str, Dict[str, Any]] = {}
        for b in bindings:
            node = _val(b, "metabolite")
            if not node:
                continue
            label = _val(b, "label")
            entry = by_node.get(node)
            if entry is None:
                by_node[node] = {
                    "identifier": _val(b, "identifier"),
                    "source": _val(b, "source"),
                    "labels": [label] if label else [],
                    "node": node,
                }
            elif label:
                entry["labels"].append(label)

        def _best_label(labels: list) -> str:
            if not labels:
                return ""
            # Prefer labels containing a lowercase letter (descriptive names)
            # over all-caps abbreviations; among those, prefer the longest.
            return sorted(
                labels,
                key=lambda s: (any(c.islower() for c in s), len(s)),
                reverse=True,
            )[0]

        metabolites = []
        for entry in by_node.values():
            metabolites.append(
                {
                    "identifier": entry["identifier"],
                    "source": entry["source"],
                    "label": _best_label(entry["labels"]),
                    "node": entry["node"],
                }
            )

        metabolites.sort(key=lambda e: (e["label"] or "").lower())

        return {
            "status": "success",
            "data": {
                "pathway_id": pathway_id,
                "metabolite_count": len(metabolites),
                "metabolites": metabolites,
            },
            "metadata": {
                "source": "WikiPathways SPARQL",
                "pathway_id": pathway_id,
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
