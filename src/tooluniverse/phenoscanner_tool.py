"""
PhenoScanner workaround tool for ToolUniverse.

PhenoScanner V2 (www.phenoscanner.medschl.cam.ac.uk) has been down since March 2024
due to a Cambridge University IT outage with no restoration timeline.

This workaround queries the EBI GWAS Catalog REST API to provide equivalent
SNP-phenotype and gene-phenotype association lookups for the GWAS catalogue.

Note: PhenoScanner also supported eQTL/pQTL/mQTL/methQTL catalogues and LD proxy
lookups. These are NOT covered by this workaround -- only GWAS associations are
available through the GWAS Catalog API.

API: https://www.ebi.ac.uk/gwas/rest/api
No authentication required.
"""

import requests
from typing import Any

from .base_tool import BaseTool
from .tool_registry import register_tool


GWAS_BASE = "https://www.ebi.ac.uk/gwas/rest/api"

_WORKAROUND_NOTE = (
    "PhenoScanner V2 is down since March 2024. This result uses the EBI GWAS "
    "Catalog as a workaround. Only GWAS associations are returned; "
    "eQTL/pQTL/mQTL/methQTL catalogues and LD proxy lookups are not available."
)


@register_tool("PhenoScannerTool")
class PhenoScannerTool(BaseTool):
    """
    Workaround for PhenoScanner V2 (broken since March 2024).

    Queries the EBI GWAS Catalog REST API for SNP-phenotype and gene-phenotype
    associations. Covers the GWAS catalogue only (not eQTL/pQTL/mQTL/methQTL).
    """

    def __init__(self, tool_config: dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        fields = tool_config.get("fields", {})
        self.operation = fields.get("operation", "query_snp")

    def run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            if self.operation == "query_snp":
                return self._query_snp(arguments)
            elif self.operation == "query_gene":
                return self._query_gene(arguments)
            return {"status": "error", "error": f"Unknown operation: {self.operation}"}
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"GWAS Catalog API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to GWAS Catalog API"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_json(self, url: str, params: dict | None = None) -> dict:
        """GET request returning JSON."""
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _query_snp(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Query phenotype associations for a SNP via GWAS Catalog."""
        rsid = arguments.get("rsid") or arguments.get("rs_id") or arguments.get("snp")
        if not rsid:
            return {"status": "error", "error": "rsid parameter is required"}
        rsid = str(rsid).strip()
        if not rsid.startswith("rs"):
            rsid = f"rs{rsid}"

        p_threshold = float(arguments.get("p_value_threshold", 1e-5))
        size = int(arguments.get("size", 100))

        url = f"{GWAS_BASE}/singleNucleotidePolymorphisms/{rsid}/associations"
        params = {"size": size}

        data = self._get_json(url, params)

        associations = data.get("_embedded", {}).get("associations", [])
        results = []
        for assoc in associations:
            p_val = assoc.get("pvalue")
            p_float = self._parse_pvalue(p_val)
            if p_float is not None and p_float > p_threshold:
                continue

            efo_traits = [
                {
                    "trait": trait.get("trait"),
                    "efo_id": trait.get("shortForm"),
                    "uri": trait.get("_links", {}).get("self", {}).get("href"),
                }
                for trait in assoc.get("efoTraits", [])
            ]

            risk_alleles = [
                {
                    "risk_allele": ra.get("riskAlleleName"),
                    "risk_frequency": ra.get("riskFrequency"),
                }
                for ra in assoc.get("loci", [{}])[0].get("strongestRiskAlleles", [])
            ]

            results.append(
                {
                    "snp": rsid,
                    "p_value": p_float,
                    "p_value_text": str(p_val) if p_val else None,
                    "or_beta": assoc.get("orPerCopyNum"),
                    "ci": assoc.get("range"),
                    "beta_direction": assoc.get("betaDirection"),
                    "beta_unit": assoc.get("betaUnit"),
                    "efo_traits": efo_traits,
                    "risk_alleles": risk_alleles,
                    "study_accession": assoc.get("study", {}).get("accessionId")
                    if isinstance(assoc.get("study"), dict)
                    else None,
                    "catalogue": "GWAS",
                }
            )

        results.sort(key=lambda x: x.get("p_value") or 1.0)

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "snp": rsid,
                "p_value_threshold": p_threshold,
                "total_associations": len(results),
                "source": "EBI GWAS Catalog (workaround for PhenoScanner)",
                "note": _WORKAROUND_NOTE,
            },
        }

    def _query_gene(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Query phenotype associations for a gene region via GWAS Catalog."""
        gene_symbol = (
            arguments.get("gene_symbol")
            or arguments.get("gene")
            or arguments.get("gene_name")
        )
        if not gene_symbol:
            return {"status": "error", "error": "gene_symbol parameter is required"}
        gene_symbol = str(gene_symbol).strip().upper()

        p_threshold = float(arguments.get("p_value_threshold", 1e-5))
        size = int(arguments.get("size", 100))

        url = f"{GWAS_BASE}/singleNucleotidePolymorphisms/search/findByGene"
        params = {"geneName": gene_symbol, "size": size}
        data = self._get_json(url, params)

        snps = data.get("_embedded", {}).get("singleNucleotidePolymorphisms", [])
        if not snps:
            return {
                "status": "success",
                "data": [],
                "metadata": {
                    "gene_symbol": gene_symbol,
                    "p_value_threshold": p_threshold,
                    "total_associations": 0,
                    "source": "EBI GWAS Catalog (workaround for PhenoScanner)",
                    "note": f"No GWAS SNPs found mapped to gene {gene_symbol}.",
                },
            }

        results = []
        seen = set()
        for snp_obj in snps[:50]:  # Limit to avoid excessive API calls
            rsid = snp_obj.get("rsId")
            if not rsid or rsid in seen:
                continue
            seen.add(rsid)

            assoc_link = snp_obj.get("_links", {}).get("associations", {}).get("href")
            if not assoc_link:
                continue

            try:
                assoc_data = self._get_json(assoc_link)
            except Exception:
                continue

            for assoc in assoc_data.get("_embedded", {}).get("associations", []):
                p_val = assoc.get("pvalue")
                p_float = self._parse_pvalue(p_val)
                if p_float is not None and p_float > p_threshold:
                    continue

                efo_traits = [
                    {
                        "trait": trait.get("trait"),
                        "efo_id": trait.get("shortForm"),
                    }
                    for trait in assoc.get("efoTraits", [])
                ]

                results.append(
                    {
                        "snp": rsid,
                        "gene": gene_symbol,
                        "p_value": p_float,
                        "or_beta": assoc.get("orPerCopyNum"),
                        "ci": assoc.get("range"),
                        "efo_traits": efo_traits,
                        "study_accession": assoc.get("study", {}).get("accessionId")
                        if isinstance(assoc.get("study"), dict)
                        else None,
                        "catalogue": "GWAS",
                    }
                )

        results.sort(key=lambda x: x.get("p_value") or 1.0)

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "gene_symbol": gene_symbol,
                "p_value_threshold": p_threshold,
                "total_associations": len(results),
                "snps_queried": len(seen),
                "source": "EBI GWAS Catalog (workaround for PhenoScanner)",
                "note": _WORKAROUND_NOTE,
            },
        }

    @staticmethod
    def _parse_pvalue(val: Any) -> float | None:
        """Parse a p-value from various formats."""
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        try:
            return float(str(val))
        except (ValueError, TypeError):
            return None
