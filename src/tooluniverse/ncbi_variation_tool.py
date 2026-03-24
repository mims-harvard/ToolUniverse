"""
NCBI Variation Services API tool for ToolUniverse.

Provides SPDI/HGVS variant notation conversion, variant normalization,
and dbSNP rsID lookup via the NCBI Variation Services API.

API: https://api.ncbi.nlm.nih.gov/variation/v0/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

NCBI_VAR_BASE = "https://api.ncbi.nlm.nih.gov/variation/v0"


@register_tool("NCBIVariationTool")
class NCBIVariationTool(BaseTool):
    """
    Tool for SPDI/HGVS variant notation conversion and normalization
    using the NCBI Variation Services API.

    Supports: spdi_to_hgvs, hgvs_to_spdi, spdi_equivalents, spdi_canonical,
    rsid_lookup.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "spdi_to_hgvs"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the NCBI Variation Services API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"NCBI Variation API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to NCBI Variation API.",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error querying NCBI Variation API: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to the appropriate endpoint."""
        dispatch = {
            "spdi_to_hgvs": self._spdi_to_hgvs,
            "hgvs_to_spdi": self._hgvs_to_spdi,
            "spdi_equivalents": self._spdi_equivalents,
            "spdi_canonical": self._spdi_canonical,
            "rsid_lookup": self._rsid_lookup,
        }
        handler = dispatch.get(self.endpoint_type)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown endpoint type: {self.endpoint_type}",
            }
        return handler(arguments)

    def _spdi_to_hgvs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Convert SPDI notation to HGVS."""
        spdi = arguments.get("spdi", "")
        if not spdi:
            return {"status": "error", "error": "spdi parameter is required"}

        url = f"{NCBI_VAR_BASE}/spdi/{spdi}/hgvs"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"API returned {resp.status_code}: {resp.text[:200]}",
            }
        data = resp.json()
        return {
            "status": "success",
            "data": data.get("data", data),
        }

    def _hgvs_to_spdi(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Convert HGVS notation to SPDI."""
        hgvs = arguments.get("hgvs", "")
        if not hgvs:
            return {"status": "error", "error": "hgvs parameter is required"}

        url = f"{NCBI_VAR_BASE}/hgvs/{hgvs}/contextuals"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"API returned {resp.status_code}: {resp.text[:200]}",
            }
        data = resp.json()
        result = data.get("data", data)
        return {
            "status": "success",
            "data": result,
        }

    def _spdi_equivalents(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get all equivalent SPDI representations across assemblies."""
        spdi = arguments.get("spdi", "")
        if not spdi:
            return {"status": "error", "error": "spdi parameter is required"}

        url = f"{NCBI_VAR_BASE}/spdi/{spdi}/all_equivalent_contextual"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"API returned {resp.status_code}: {resp.text[:200]}",
            }
        data = resp.json()
        spdis = data.get("data", {}).get("spdis", [])
        return {
            "status": "success",
            "data": {
                "equivalents": spdis,
                "count": len(spdis),
            },
        }

    def _spdi_canonical(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get canonical representative SPDI for a variant."""
        spdi = arguments.get("spdi", "")
        if not spdi:
            return {"status": "error", "error": "spdi parameter is required"}

        url = f"{NCBI_VAR_BASE}/spdi/{spdi}/canonical_representative"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"API returned {resp.status_code}: {resp.text[:200]}",
            }
        data = resp.json()
        return {
            "status": "success",
            "data": data.get("data", data),
        }

    def _rsid_lookup(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Look up a dbSNP rsID and return variant details."""
        rsid = arguments.get("rsid", "")
        if not rsid:
            return {"status": "error", "error": "rsid parameter is required"}

        # Strip 'rs' prefix if present
        rsid_num = rsid.lstrip("rs")
        if not rsid_num.isdigit():
            return {
                "status": "error",
                "error": f"Invalid rsID: '{rsid}'. Must be numeric or start with 'rs'.",
            }

        url = f"{NCBI_VAR_BASE}/refsnp/{rsid_num}"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"API returned {resp.status_code}: {resp.text[:200]}",
            }
        data = resp.json()

        # Extract key information from the large response
        result = {
            "refsnp_id": data.get("refsnp_id"),
            "create_date": data.get("create_date"),
            "last_update_date": data.get("last_update_date"),
            "citations": data.get("citations", []),
            "mane_select_ids": data.get("mane_select_ids", []),
        }

        # Extract primary snapshot data
        snapshot = data.get("primary_snapshot_data", {})
        if snapshot:
            result["organism"] = snapshot.get("organism")
            result["variant_type"] = snapshot.get("variant_type")

            # Extract placements for GRCh38
            placements = snapshot.get("placements_with_allele", [])
            grch38_placements = []
            for p in placements:
                assembly = p.get("placement_annot", {}).get(
                    "seq_id_traits_by_assembly", []
                )
                for a in assembly:
                    if "GRCh38" in a.get("assembly_name", ""):
                        alleles = p.get("alleles", [])
                        for allele in alleles:
                            spdi = allele.get("allele", {}).get("spdi", {})
                            if spdi:
                                grch38_placements.append(
                                    {
                                        "seq_id": spdi.get("seq_id"),
                                        "position": spdi.get("position"),
                                        "deleted_sequence": spdi.get(
                                            "deleted_sequence"
                                        ),
                                        "inserted_sequence": spdi.get(
                                            "inserted_sequence"
                                        ),
                                    }
                                )
                        break

            if grch38_placements:
                result["grch38_placements"] = grch38_placements

            # Extract allele annotations (clinical significance, frequency)
            allele_annots = snapshot.get("allele_annotations", [])
            if allele_annots:
                clinical = []
                for annot in allele_annots:
                    for assembly_annot in annot.get("assembly_annotation", []):
                        for gene in assembly_annot.get("genes", []):
                            clinical.append(
                                {
                                    "gene": gene.get("locus"),
                                    "name": gene.get("name"),
                                    "gene_id": gene.get("id"),
                                }
                            )
                if clinical:
                    result["genes"] = clinical

                # Extract clinical significance
                for annot in allele_annots:
                    clin = annot.get("clinical", [])
                    if clin:
                        result["clinical_significance"] = [
                            {
                                "accession": c.get("accession_version"),
                                "review_status": c.get("review_status"),
                                "disease_names": c.get("disease_names", []),
                                "significance": c.get("clinical_significances", []),
                            }
                            for c in clin[:5]  # Limit to first 5
                        ]

        return {
            "status": "success",
            "data": result,
        }
