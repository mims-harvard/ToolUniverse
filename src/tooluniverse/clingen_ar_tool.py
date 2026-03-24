# clingen_ar_tool.py
"""
ClinGen Allele Registry API tool for ToolUniverse.

The ClinGen Allele Registry provides canonical identifiers (CA IDs) for
genetic variants, normalizing representations across different nomenclatures
and coordinate systems. It links to ClinVar, dbSNP, COSMIC, gnomAD, and
other variant databases.

API: https://reg.clinicalgenome.org/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

CLINGEN_AR_BASE_URL = "https://reg.clinicalgenome.org"


@register_tool("ClinGenARTool")
class ClinGenARTool(BaseTool):
    """
    Tool for querying the ClinGen Allele Registry.

    The Allele Registry normalizes variant nomenclature and provides
    canonical allele identifiers (CA IDs) that link to ClinVar, dbSNP,
    COSMIC, gnomAD, and other variant databases. Supports HGVS notation
    lookup and external record retrieval.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "lookup_allele")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the ClinGen Allele Registry API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"ClinGen AR API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to ClinGen Allele Registry",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"ClinGen AR API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying ClinGen AR: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate ClinGen AR endpoint."""
        if self.endpoint == "lookup_allele":
            return self._lookup_allele(arguments)
        elif self.endpoint == "get_external_records":
            return self._get_external_records(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _lookup_allele(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Look up a variant by HGVS notation."""
        hgvs = arguments.get("hgvs", "")
        if not hgvs:
            return {"status": "error", "error": "hgvs parameter is required"}

        url = f"{CLINGEN_AR_BASE_URL}/allele"
        params = {"hgvs": hgvs}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()

        # Extract allele ID from @id URL
        allele_url = data.get("@id", "")
        allele_id = allele_url.split("/")[-1] if allele_url else None

        # Extract community standard title
        titles = data.get("communityStandardTitle", [])
        title = titles[0] if titles else None

        # Extract external records summary
        external_records = data.get("externalRecords", {})

        # Extract genomic alleles
        genomic_alleles = []
        for ga in data.get("genomicAlleles", []):
            hgvs_list = ga.get("hgvs", [])
            genomic_alleles.append(
                {
                    "hgvs": hgvs_list[0] if hgvs_list else None,
                    "reference_genome": ga.get("referenceGenome"),
                }
            )

        return {
            "status": "success",
            "data": {
                "allele_id": allele_id,
                "allele_url": allele_url,
                "community_standard_title": title,
                "external_records": external_records,
                "genomic_alleles": genomic_alleles,
            },
            "metadata": {
                "source": "ClinGen Allele Registry",
                "query_hgvs": hgvs,
            },
        }

    def _get_external_records(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get external database records for a canonical allele ID."""
        allele_id = arguments.get("allele_id", "")
        if not allele_id:
            return {"status": "error", "error": "allele_id parameter is required"}

        url = f"{CLINGEN_AR_BASE_URL}/allele/{allele_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()

        # Extract community standard title
        titles = data.get("communityStandardTitle", [])
        title = titles[0] if titles else None

        # Extract external records
        external_records = data.get("externalRecords", {})

        # Build database summary
        databases = {}
        for db_name, records in external_records.items():
            if isinstance(records, list):
                db_entries = []
                for rec in records:
                    entry = {
                        "id": rec.get("id"),
                        "url": rec.get("@id"),
                    }
                    if "variationId" in rec:
                        entry["variation_id"] = rec["variationId"]
                    db_entries.append(entry)
                databases[db_name] = db_entries

        return {
            "status": "success",
            "data": {
                "allele_id": allele_id,
                "community_standard_title": title,
                "databases": databases,
                "database_count": len(databases),
            },
            "metadata": {
                "source": "ClinGen Allele Registry",
                "query_allele_id": allele_id,
            },
        }
