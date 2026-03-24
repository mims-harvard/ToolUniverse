"""
ClinGen Allele Registry Tool - Canonical Allele Identifiers

The ClinGen Allele Registry assigns globally unique canonical allele identifiers
(CA IDs) to genetic variants. It links variants across databases (ClinVar, dbSNP,
COSMIC, gnomAD, ExAC) and provides standardized HGVS nomenclature.

API: https://reg.clinicalgenome.org/ (also reg.genome.network)
Reference: Pawliczek et al. (2018) Human Mutation
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

CLINGEN_REG_BASE = "https://reg.clinicalgenome.org"


@register_tool("ClinGenAlleleTool")
class ClinGenAlleleTool(BaseTool):
    """Look up canonical allele identifiers and cross-database links."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _lookup_hgvs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Look up a variant by HGVS expression to get canonical allele ID."""
        hgvs = params.get("hgvs", "")
        if not hgvs:
            return {"status": "error", "error": "hgvs parameter is required"}

        resp = self.session.get(
            f"{CLINGEN_REG_BASE}/allele",
            params={"hgvs": hgvs},
            timeout=30,
        )
        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"No allele found for HGVS: {hgvs}",
            }
        if resp.status_code != 200:
            body = resp.text[:300]
            return {
                "status": "error",
                "error": f"ClinGen lookup failed: HTTP {resp.status_code} - {body}",
            }

        data = resp.json()
        # Check for error responses (e.g., incorrect reference allele)
        if "errorType" in data:
            return {
                "status": "error",
                "error": f"{data.get('errorType')}: {data.get('message', data.get('description', ''))}",
            }

        return self._format_allele(data)

    def _get_allele(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information for a canonical allele by CA ID."""
        ca_id = params.get("ca_id") or params.get("allele_id", "")
        if not ca_id:
            return {
                "status": "error",
                "error": "ca_id (or allele_id) parameter is required",
            }

        url = f"{CLINGEN_REG_BASE}/allele/{ca_id}"
        resp = self.session.get(url, timeout=30)
        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"Allele '{ca_id}' not found",
            }
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"ClinGen request failed: HTTP {resp.status_code}",
            }

        return self._format_allele(resp.json())

    def _format_allele(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format allele response into structured result."""
        allele_id = data.get("@id", "")
        ca_id = allele_id.split("/")[-1] if allele_id else None

        # Extract external records
        ext = data.get("externalRecords", {})
        external_ids = {}
        for db_name, records in ext.items():
            if isinstance(records, list):
                external_ids[db_name] = [
                    r.get("id") or r.get("preferredName") or r.get("@id", "")
                    for r in records[:5]
                ]

        # Extract genomic coordinates
        genomic = []
        for ga in data.get("genomicAlleles") or []:
            for coord in ga.get("coordinates") or []:
                genomic.append(
                    {
                        "chromosome": ga.get("chromosome"),
                        "start": coord.get("start"),
                        "end": coord.get("end"),
                        "allele": coord.get("allele"),
                        "reference_allele": coord.get("referenceAllele"),
                        "reference_genome": coord.get("referenceGenome"),
                    }
                )

        # Extract transcript alleles
        transcripts = []
        for ta in (data.get("transcriptAlleles") or [])[:10]:
            hgvs_list = ta.get("hgvs") or []
            transcripts.append(
                {
                    "hgvs": hgvs_list[:3] if hgvs_list else [],
                    "gene_symbol": ta.get("geneSymbol"),
                    "protein_effect": ta.get("proteinEffect", {}).get("hgvs")
                    if ta.get("proteinEffect")
                    else None,
                }
            )

        result = {
            "ca_id": ca_id,
            "community_standard_title": data.get("communityStandardTitle", []),
            "external_records": external_ids,
            "genomic_alleles": genomic[:5],
            "transcript_alleles": transcripts,
        }
        return {
            "status": "success",
            "data": result,
            "metadata": {"ca_id": ca_id},
        }

    def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        operation = self.tool_config.get("fields", {}).get("operation", "")
        if operation == "lookup_hgvs":
            return self._lookup_hgvs(params)
        if operation == "get_allele":
            return self._get_allele(params)
        return {"status": "error", "error": f"Unknown operation: {operation}"}
