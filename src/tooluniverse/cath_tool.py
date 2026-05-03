# cath_tool.py
"""
CATH Protein Structure Classification Database API tool for ToolUniverse.

CATH is a hierarchical classification of protein domain structures that
clusters proteins at four major levels: Class (C), Architecture (A),
Topology (T), and Homologous superfamily (H). CATH classifies domains
from the PDB and AlphaFold Protein Structure Database.

API: https://www.cathdb.info/version/v4_3_0/api/rest/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

CATH_BASE_URL = "https://www.cathdb.info/version/v4_3_0/api/rest"


@register_tool("CATHTool")
class CATHTool(BaseTool):
    """
    Tool for querying the CATH protein structure classification database.

    CATH classifies protein domain structures into a hierarchy:
    Class -> Architecture -> Topology -> Homologous superfamily.
    Covers 500,000+ domains from PDB and AFDB structures.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "superfamily")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the CATH API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"CATH API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to CATH API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"CATH API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying CATH: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate CATH endpoint."""
        if self.endpoint == "superfamily":
            return self._get_superfamily(arguments)
        elif self.endpoint == "domain_summary":
            return self._get_domain_summary(arguments)
        elif self.endpoint == "list_funfams":
            return self._list_funfams(arguments)
        elif self.endpoint == "get_funfam":
            return self._get_funfam(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _get_superfamily(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get CATH superfamily information by CATH ID."""
        cath_id = arguments.get("superfamily_id", "")
        if not cath_id:
            return {
                "status": "error",
                "error": "superfamily_id parameter is required (e.g. 2.40.50.140 for Nucleic acid-binding proteins)",
            }

        url = f"{CATH_BASE_URL}/superfamily/{cath_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        resp_data = response.json()

        if not resp_data.get("success"):
            return {
                "status": "error",
                "error": f"CATH API returned unsuccessful response for {cath_id}",
            }

        data = resp_data.get("data", {})

        result = {
            "cath_id": data.get("cath_id"),
            "superfamily_id": data.get("superfamily_id"),
            "classification_name": data.get("classification_name"),
            "classification_description": data.get("classification_description"),
            "example_domain_id": data.get("example_domain_id"),
            "num_s35_families": data.get("child_count_s35_code"),
            "num_s60_families": data.get("child_count_s60_code"),
            "num_s95_families": data.get("child_count_s95_code"),
            "num_s100_domains": data.get("child_count_s100_code"),
            "total_domain_count": data.get("child_count_s100_count"),
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "CATH v4.3.0",
                "query": cath_id,
            },
        }

    def _get_domain_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get domain summary for a CATH domain ID (PDB chain domain)."""
        domain_id = arguments.get("domain_id", "")
        if not domain_id:
            return {
                "status": "error",
                "error": "domain_id parameter is required (e.g. 1cukA01 for PDB 1CUK chain A domain 1)",
            }

        url = f"{CATH_BASE_URL}/domain_summary/{domain_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        resp_data = response.json()

        data = resp_data.get("data", {})

        # Extract CATH classification from cath_id
        cath_id = data.get("cath_id", "")
        cath_parts = cath_id.split(".") if cath_id else []

        result = {
            "domain_id": domain_id,
            "cath_id": cath_id,
            "superfamily_id": data.get("superfamily_id"),
            "class": cath_parts[0] if len(cath_parts) > 0 else None,
            "architecture": ".".join(cath_parts[:2]) if len(cath_parts) > 1 else None,
            "topology": ".".join(cath_parts[:3]) if len(cath_parts) > 2 else None,
            "homologous_superfamily": ".".join(cath_parts[:4])
            if len(cath_parts) > 3
            else None,
            "residue_count": len(data.get("residues", [])),
        }

        # CATH class names
        class_names = {
            "1": "Mainly Alpha",
            "2": "Mainly Beta",
            "3": "Alpha Beta",
            "4": "Few Secondary Structures",
        }
        if result["class"] in class_names:
            result["class_name"] = class_names[result["class"]]

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "CATH v4.3.0",
                "query": domain_id,
            },
        }

    def _list_funfams(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List functional families (FunFams) within a CATH superfamily."""
        superfamily_id = arguments.get("superfamily_id", "")
        if not superfamily_id:
            return {
                "status": "error",
                "error": "superfamily_id is required (e.g., '1.10.510.10' for Globin-like)",
            }

        url = f"{CATH_BASE_URL}/superfamily/{superfamily_id}/funfam"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        resp_data = response.json()

        funfams_raw = resp_data.get("data", [])
        max_results = arguments.get("max_results", 25)

        funfams = []
        for ff in funfams_raw[:max_results]:
            funfams.append(
                {
                    "funfam_number": ff.get("funfam_number"),
                    "name": ff.get("name"),
                    "num_members": ff.get("num_members_in_funfam"),
                    "rep_id": ff.get("rep_id"),
                    "superfamily_id": ff.get("superfamily_id"),
                }
            )

        return {
            "status": "success",
            "data": {
                "superfamily_id": superfamily_id,
                "total_funfams": len(funfams_raw),
                "funfams": funfams,
            },
            "metadata": {
                "source": "CATH v4.3.0",
                "query": superfamily_id,
            },
        }

    def _get_funfam(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get details for a specific FunFam within a CATH superfamily."""
        superfamily_id = arguments.get("superfamily_id", "")
        funfam_number = arguments.get("funfam_number", "")
        if not superfamily_id or not funfam_number:
            return {
                "status": "error",
                "error": "Both superfamily_id and funfam_number are required",
            }

        url = f"{CATH_BASE_URL}/superfamily/{superfamily_id}/funfam/{funfam_number}"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        resp_data = response.json()

        data = resp_data.get("data", {})
        result = {
            "funfam_number": data.get("funfam_number"),
            "superfamily_id": data.get("superfamily_id"),
            "name": data.get("name"),
            "description": data.get("description"),
            "num_members": data.get("num_members_in_funfam"),
            "num_seed_members": data.get("num_members_in_seed_aln"),
            "dops_score": data.get("seed_dops_score"),
            "rep_id": data.get("rep_id"),
            "ec_terms": data.get("ec_terms", []),
            "go_terms": data.get("go_terms", []),
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "CATH v4.3.0",
                "query": f"{superfamily_id}/funfam/{funfam_number}",
            },
        }
