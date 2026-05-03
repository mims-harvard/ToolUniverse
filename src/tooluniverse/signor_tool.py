"""
SIGNOR Tool - SIGnaling Network Open Resource

SIGNOR is a database of causal relationships between biological entities
(proteins, chemicals, complexes, phenotypes) in cell signaling. Each
relationship describes how entity A affects entity B through a specific
mechanism (phosphorylation, ubiquitination, transcriptional regulation, etc.).

API: https://signor.uniroma2.it/getData.php (TSV format)
Pathways: https://signor.uniroma2.it/getPathwayData.php
Reference: Licata et al. (2020) Nucleic Acids Research
"""

import requests
from functools import lru_cache
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

SIGNOR_DATA_URL = "https://signor.uniroma2.it/getData.php"
SIGNOR_PATHWAY_URL = "https://signor.uniroma2.it/getPathwayData.php"
UNIPROT_SEARCH_URL = "https://rest.uniprot.org/uniprotkb/search"


@lru_cache(maxsize=256)
def _resolve_gene_to_uniprot(gene_symbol: str, taxon_id: int = 9606) -> str:
    """Resolve a gene symbol to a reviewed UniProt accession (cached per process)."""
    try:
        resp = requests.get(
            UNIPROT_SEARCH_URL,
            params={
                "query": f"gene_exact:{gene_symbol} AND organism_id:{taxon_id} AND reviewed:true",
                "fields": "accession",
                "format": "json",
                "size": 1,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            hits = resp.json().get("results", [])
            if hits:
                return hits[0].get("primaryAccession", "")
    except Exception:
        pass
    return ""


# Column names for getData.php TSV response (no header row)
DATA_COLUMNS = [
    "entitya",
    "typea",
    "ida",
    "databasea",
    "entityb",
    "typeb",
    "idb",
    "databaseb",
    "effect",
    "mechanism",
    "residue",
    "sequence",
    "tax_id",
    "cell_data",
    "tissue_data",
    "modulator_complex",
    "target_complex",
    "modificationa",
    "modaseq",
    "modificationb",
    "modbseq",
    "pmid",
    "direct",
    "notes",
    "annotator",
    "sentence",
    "signor_id",
    "score",
]


def _parse_tsv(
    text: str, columns: List[str], has_header: bool = False
) -> List[Dict[str, str]]:
    """Parse TSV text into list of dicts."""
    lines = text.strip().split("\n")
    if not lines:
        return []
    start = 1 if has_header else 0
    results = []
    for line in lines[start:]:
        if not line.strip():
            continue
        fields = line.split("\t")
        row = {}
        for i, col in enumerate(columns):
            row[col] = fields[i].strip() if i < len(fields) else ""
        results.append(row)
    return results


def _format_interaction(row: Dict[str, str]) -> Dict[str, Any]:
    """Convert a parsed TSV row into a structured interaction dict."""
    return {
        "source_entity": row.get("entitya", ""),
        "source_type": row.get("typea", ""),
        "source_id": row.get("ida", ""),
        "target_entity": row.get("entityb", ""),
        "target_type": row.get("typeb", ""),
        "target_id": row.get("idb", ""),
        "effect": row.get("effect", ""),
        "mechanism": row.get("mechanism", ""),
        "residue": row.get("residue", "") or None,
        "pmid": row.get("pmid", "") or None,
        "direct": row.get("direct", "") == "t",
        "score": float(row["score"]) if row.get("score") else None,
        "signor_id": row.get("signor_id", ""),
    }


@register_tool("SIGNORTool")
class SIGNORTool(BaseTool):
    """Query SIGNOR for causal signaling relationships and pathways."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.session = requests.Session()

    def _get_interactions(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get signaling interactions for a protein/entity."""
        entity_id = (
            params.get("entity_id")
            or params.get("protein")
            or params.get("uniprot_id")
            or ""
        )
        organism = params.get("organism", 9606)
        limit = params.get("limit", 50)
        if not entity_id:
            return {
                "status": "error",
                "error": "entity_id parameter is required (e.g., UniProt ID like P04637)",
            }

        resp = self.session.get(
            SIGNOR_DATA_URL,
            params={"organism": organism, "id": entity_id},
            timeout=30,
        )
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"SIGNOR request failed: HTTP {resp.status_code}",
            }

        # If no results and input looks like a gene symbol, try resolving to UniProt ID
        if resp.text.strip() in (
            "",
            "No result found.",
        ) or resp.text.strip().startswith("<!"):
            resolved = _resolve_gene_to_uniprot(entity_id, organism)
            if resolved and resolved != entity_id:
                resp2 = self.session.get(
                    SIGNOR_DATA_URL,
                    params={"organism": organism, "id": resolved},
                    timeout=30,
                )
                if (
                    resp2.status_code == 200
                    and resp2.text.strip()
                    and not resp2.text.strip().startswith("<!")
                    and resp2.text.strip() != "No result found."
                ):
                    resp = resp2
                    entity_id = resolved
                else:
                    return {
                        "status": "error",
                        "error": f"No interactions found for '{params.get('entity_id') or params.get('protein')}' (resolved to UniProt {resolved}) in organism {organism}. SIGNOR requires UniProt accessions (e.g., P04637 for TP53).",
                    }
            else:
                return {
                    "status": "error",
                    "error": f"No interactions found for '{entity_id}' in organism {organism}. SIGNOR requires UniProt accessions (e.g., P04637 for TP53).",
                }

        rows = _parse_tsv(resp.text, DATA_COLUMNS, has_header=False)
        interactions = [_format_interaction(row) for row in rows[:limit]]
        return {
            "status": "success",
            "data": interactions,
            "metadata": {
                "entity_id": entity_id,
                "organism": organism,
                "total_interactions": len(rows),
                "returned": len(interactions),
            },
        }

    def _list_pathways(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List all SIGNOR curated signaling pathways."""
        resp = self.session.get(
            SIGNOR_PATHWAY_URL,
            params={"description": ""},
            timeout=30,
        )
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"SIGNOR pathway list failed: HTTP {resp.status_code}",
            }

        cols = ["sig_id", "path_name", "path_description", "path_curator"]
        rows = _parse_tsv(resp.text, cols, has_header=True)

        query = params.get("query", "").lower()
        if query:
            rows = [
                r
                for r in rows
                if query in r.get("path_name", "").lower()
                or query in r.get("path_description", "").lower()
            ]

        pathways = [
            {
                "pathway_id": r.get("sig_id", ""),
                "name": r.get("path_name", ""),
                "description": r.get("path_description", "")[:300] or None,
                "curator": r.get("path_curator", "") or None,
            }
            for r in rows
        ]
        return {
            "status": "success",
            "data": pathways,
            "metadata": {"total_pathways": len(pathways)},
        }

    def _get_pathway(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get interactions belonging to a specific SIGNOR pathway."""
        pathway_id = params.get("pathway_id", "")
        limit = params.get("limit", 100)
        if not pathway_id:
            return {
                "status": "error",
                "error": "pathway_id is required (e.g., SIGNOR-AD, SIGNOR-C)",
            }

        resp = self.session.get(
            SIGNOR_PATHWAY_URL,
            params={"pathway": pathway_id, "relations": "only"},
            timeout=30,
        )
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"SIGNOR pathway request failed: HTTP {resp.status_code}",
            }

        if not resp.text.strip():
            return {
                "status": "error",
                "error": f"Pathway '{pathway_id}' not found",
            }

        # Pathway relations have a header row with columns
        path_cols = [
            "pathway_id",
            "pathway_name",
            "entitya",
            "regulator_location",
            "typea",
            "ida",
            "databasea",
            "entityb",
            "target_location",
            "typeb",
            "idb",
            "databaseb",
            "effect",
            "mechanism",
            "residue",
            "sequence",
            "tax_id",
            "cell_data",
            "tissue_data",
            "modulator_complex",
            "target_complex",
            "modificationa",
            "modaseq",
            "modificationb",
            "modbseq",
            "pmid",
            "direct",
            "annotator",
            "sentence",
            "notes",
            "signor_id",
            "score",
        ]
        rows = _parse_tsv(resp.text, path_cols, has_header=True)
        interactions = [_format_interaction(row) for row in rows[:limit]]
        return {
            "status": "success",
            "data": interactions,
            "metadata": {
                "pathway_id": pathway_id,
                "total_interactions": len(rows),
                "returned": len(interactions),
            },
        }

    def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        operation = self.tool_config.get("fields", {}).get("operation", "")
        if operation == "get_interactions":
            return self._get_interactions(params)
        if operation == "list_pathways":
            return self._list_pathways(params)
        if operation == "get_pathway":
            return self._get_pathway(params)
        return {"status": "error", "error": f"Unknown operation: {operation}"}
