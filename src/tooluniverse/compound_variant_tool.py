"""Compound tool: annotate a variant from multiple sources in one call.

Queries ClinVar, gnomAD, CIViC, and UniProt for a given variant,
cross-references results, and returns a unified annotation with
pathogenicity classification, population frequencies, and clinical evidence.
"""

import re
from typing import Any, Dict, List

from .base_tool import BaseTool
from .tool_registry import register_tool

_AA_1TO3 = {
    "A": "Ala",
    "R": "Arg",
    "N": "Asn",
    "D": "Asp",
    "C": "Cys",
    "E": "Glu",
    "Q": "Gln",
    "G": "Gly",
    "H": "His",
    "I": "Ile",
    "L": "Leu",
    "K": "Lys",
    "M": "Met",
    "F": "Phe",
    "P": "Pro",
    "S": "Ser",
    "T": "Thr",
    "W": "Trp",
    "Y": "Tyr",
    "V": "Val",
    "X": "Ter",
    "*": "Ter",
}


def _variant_match_forms(token: str) -> List[str]:
    """Expand a protein change like 'V600E' to the forms that appear in records:
    the short form plus the HGVS 3-letter form ('Val600Glu') ClinVar titles use."""
    forms = [token.lower()]
    m = re.fullmatch(r"([A-Za-z])(\d+)([A-Za-z*])", token.strip())
    if m:
        ref, pos, alt = m.group(1).upper(), m.group(2), m.group(3).upper()
        if ref in _AA_1TO3 and alt in _AA_1TO3:
            forms.append(f"{_AA_1TO3[ref]}{pos}{_AA_1TO3[alt]}".lower())
    return forms


def _title_matches(name: str, token: str) -> bool:
    low = str(name).lower()
    return any(f in low for f in _variant_match_forms(token))


@register_tool("CompoundVariantAnnotationTool")
class CompoundVariantAnnotationTool(BaseTool):
    """Annotate a variant from ClinVar, gnomAD, CIViC, and UniProt in one call."""

    def __init__(self, tool_config: Dict[str, Any], **kwargs):
        super().__init__(tool_config)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        variant = arguments.get("variant")
        gene = arguments.get("gene") or arguments.get("gene_symbol")
        rsid = arguments.get("rsid")

        if not variant and not gene and not rsid:
            return {
                "status": "error",
                "error": "At least one of 'variant', 'gene', or 'rsid' is required.",
            }

        from .execute_function import ToolUniverse

        tu = ToolUniverse()
        tu.load_tools()

        annotations: Dict[str, Any] = {}
        sources_failed: List[str] = []

        # Resolve the gene up front: ClinVar/CIViC/gnomAD/UniProt are all queried by
        # gene (or rsid), NOT by a bare protein change like "V600E" (which matches
        # nothing in ClinVar). Derive the gene from the explicit arg or the variant.
        gene_for_gnomad = gene
        if not gene_for_gnomad and variant:
            parts = variant.split()
            if parts:
                gene_for_gnomad = parts[0]
        # The protein-change token (e.g. "V600E") used to filter gene-level hits.
        variant_token = None
        if variant:
            toks = variant.split()
            variant_token = toks[-1] if toks else variant

        # 1. ClinVar — query by rsid (precise) or gene; a bare protein change returns 0.
        clinvar_query = rsid or gene_for_gnomad or variant
        if clinvar_query:
            try:
                r = tu.run_one_function(
                    {
                        "name": "ClinVar_search_variants",
                        "arguments": {"query": clinvar_query, "limit": 20},
                    }
                )
                annotations["clinvar"] = self._parse_clinvar(r, variant_token)
            except Exception as e:
                sources_failed.append(f"ClinVar: {str(e)[:100]}")

        # 2. gnomAD
        if gene_for_gnomad:
            try:
                r = tu.run_one_function(
                    {
                        "name": "gnomad_get_gene",
                        "arguments": {"gene_symbol": gene_for_gnomad},
                    }
                )
                annotations["gnomad"] = self._parse_gnomad(r)
            except Exception as e:
                sources_failed.append(f"gnomAD: {str(e)[:100]}")

        # 3. CIViC
        if gene_for_gnomad:
            try:
                r = tu.run_one_function(
                    {
                        "name": "civic_get_variants_by_gene",
                        "arguments": {"gene_symbol": gene_for_gnomad},
                    }
                )
                annotations["civic"] = self._parse_civic(r, variant_token)
            except Exception as e:
                sources_failed.append(f"CIViC: {str(e)[:100]}")

        # 4. UniProt
        if gene_for_gnomad:
            try:
                r = tu.run_one_function(
                    {
                        "name": "UniProt_search",
                        "arguments": {
                            "query": gene_for_gnomad,
                            "organism": "human",
                            "limit": 3,
                        },
                    }
                )
                annotations["uniprot"] = self._parse_uniprot(r)
            except Exception as e:
                sources_failed.append(f"UniProt: {str(e)[:100]}")

        # Build summary
        summary = self._build_summary(annotations, variant, gene_for_gnomad, rsid)

        return {
            "status": "success",
            "data": {
                "query": {"variant": variant, "gene": gene, "rsid": rsid},
                "sources_queried": list(annotations.keys()),
                "sources_failed": sources_failed,
                "summary": summary,
                "annotations": annotations,
            },
        }

    def _parse_clinvar(self, result: Any, variant_token: str = None) -> Dict[str, Any]:
        if not isinstance(result, dict):
            return {"raw": str(result)[:200]}
        data = result.get("data", {})
        variants = data.get("variants", []) if isinstance(data, dict) else []

        def _row(v: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "name": v.get("title", v.get("name", "")),
                "classification": v.get(
                    "clinical_significance", v.get("classification", "")
                ),
                "condition": v.get("condition", ""),
                "review_status": v.get("review_status", ""),
            }

        rows = [v for v in variants if isinstance(v, dict)]
        matched = [
            _row(v)
            for v in rows
            if variant_token
            and _title_matches(v.get("title", v.get("name", "")), variant_token)
        ]
        # If the specific change isn't found (ClinVar titles use HGVS), still return
        # the top gene-level variants as context rather than a misleading empty result.
        variants_out = matched if matched else [_row(v) for v in rows[:10]]
        return {
            "total_gene_variants": data.get("total_count", 0),
            "matched": len(matched),
            "exact_match": bool(matched),
            "variants": variants_out[:10],
        }

    def _parse_gnomad(self, result: Any) -> Dict[str, Any]:
        if not isinstance(result, dict):
            return {"raw": str(result)[:200]}
        # gnomad_get_gene nests the record under data.gene.
        gene = (result.get("data") or {}).get("gene") or {}
        if isinstance(gene, dict) and gene.get("gene_id"):
            return {
                "gene_id": gene.get("gene_id"),
                "symbol": gene.get("symbol"),
                "name": gene.get("name"),
                "chromosome": gene.get("chrom"),
                "canonical_transcript": gene.get("canonical_transcript_id"),
            }
        return {}

    def _parse_civic(self, result: Any, variant_token: str = None) -> Dict[str, Any]:
        if not isinstance(result, dict):
            return {"raw": str(result)[:200]}
        # civic_get_variants_by_gene returns data.gene.variants.nodes (a list).
        gene = (result.get("data") or {}).get("gene") or {}
        nodes = ((gene.get("variants") or {}) if isinstance(gene, dict) else {}).get(
            "nodes", []
        )
        parsed = []
        for v in nodes if isinstance(nodes, list) else []:
            if not isinstance(v, dict):
                continue
            name = v.get("name", v.get("variant_name", ""))
            if variant_token and not _title_matches(name, variant_token):
                continue
            parsed.append(
                {
                    "name": name,
                    "civic_id": v.get("id"),
                    "feature": (v.get("feature") or {}).get("name")
                    if isinstance(v.get("feature"), dict)
                    else v.get("feature"),
                }
            )
        return {
            "total_gene_variants": len(nodes) if isinstance(nodes, list) else 0,
            "matched": len(parsed),
            "variants": parsed[:20],
        }

    def _parse_uniprot(self, result: Any) -> Dict[str, Any]:
        if not isinstance(result, dict):
            return {"raw": str(result)[:200]}
        data = result.get("data", {})
        if isinstance(data, list) and data:
            entry = data[0]
            return {
                "accession": entry.get("accession", ""),
                "protein_name": entry.get("protein_name", ""),
                "gene_name": entry.get("gene_name", ""),
                "function": str(entry.get("function", ""))[:300],
            }
        return {"raw": str(data)[:200]}

    def _build_summary(
        self,
        annotations: Dict[str, Any],
        variant: str = None,
        gene: str = None,
        rsid: str = None,
    ) -> Dict[str, Any]:
        summary = {"query": variant or gene or rsid, "sources_with_data": []}

        # A source counts as "with data" only if it returned actual results — not
        # merely because the sub-call did not throw.
        def _has_data(source: str, d: Dict[str, Any]) -> bool:
            if not isinstance(d, dict) or d.get("raw"):
                return False
            if source == "clinvar":
                return bool(d.get("variants"))
            if source == "civic":
                return bool(d.get("variants"))
            if source == "gnomad":
                return bool(d.get("gene_id"))
            if source == "uniprot":
                return bool(d.get("accession"))
            return bool(d)

        for source, data in annotations.items():
            if _has_data(source, data):
                summary["sources_with_data"].append(source)

        clinvar = annotations.get("clinvar", {})
        if clinvar.get("variants"):
            classifications = [
                v["classification"]
                for v in clinvar["variants"]
                if v.get("classification")
            ]
            if classifications:
                summary["clinvar_classification"] = classifications[0]

        gnomad = annotations.get("gnomad", {})
        if gnomad.get("gene_id"):
            summary["gnomad_gene_id"] = gnomad["gene_id"]

        civic = annotations.get("civic", {})
        if civic.get("matched"):
            summary["civic_variants_matched"] = civic["matched"]

        return summary
