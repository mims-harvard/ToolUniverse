"""
iPTMnet Tool - Post-Translational Modification Network Database

Provides access to the iPTMnet REST API for querying post-translational
modification (PTM) data, including modification sites, proteoforms,
PTM-dependent protein-protein interactions, and enzyme-substrate relationships.

iPTMnet integrates data from PhosphoSitePlus, UniProt, PRO ontology, and
literature mining to provide a comprehensive view of the PTM landscape.

API base: https://research.bioinformatics.udel.edu/iptmnet/api
No authentication required.

Reference: Huang et al., Bioinformatics 2018
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool


IPTMNET_BASE_URL = "https://research.bioinformatics.udel.edu/iptmnet/api"


@register_tool("iPTMnetTool")
class iPTMnetTool(BaseTool):
    """
    Tool for querying the iPTMnet PTM network database.

    Supported operations:
    - search: Search proteins by name/keyword with role and PTM type filters
    - get_ptm_sites: Get all PTM sites for a protein (phosphorylation, etc.)
    - get_proteoforms: Get proteoform records with specific PTM combinations
    - get_ptm_ppi: Get PTM-dependent protein-protein interactions
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.session = requests.Session()
        self.timeout = 30

    def _infer_operation(self, arguments: Dict[str, Any]) -> str:
        """Infer operation from tool name when not explicitly provided."""
        tool_name = self.tool_config.get("name", "")
        if "search" in tool_name.lower():
            return "search"
        if "ptm_sites" in tool_name.lower():
            return "get_ptm_sites"
        if "proteoform" in tool_name.lower():
            return "get_proteoforms"
        if "ptm_ppi" in tool_name.lower():
            return "get_ptm_ppi"
        return ""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the iPTMnet API tool with given arguments."""
        operation = arguments.get("operation") or self._infer_operation(arguments)
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        handlers = {
            "search": self._search,
            "get_ptm_sites": self._get_ptm_sites,
            "get_proteoforms": self._get_proteoforms,
            "get_ptm_ppi": self._get_ptm_ppi,
        }

        handler = handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": "Unknown operation: {}. Available: {}".format(
                    operation, list(handlers.keys())
                ),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "iPTMnet API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to iPTMnet API"}
        except Exception as e:
            return {"status": "error", "error": "iPTMnet API error: {}".format(str(e))}

    def _fetch_protein_data(self, uniprot_id: str, endpoint: str) -> Dict[str, Any]:
        """Fetch data for a protein from iPTMnet. Returns parsed JSON or error dict."""
        resp = self.session.get(
            "{}/{}/{}".format(IPTMNET_BASE_URL, uniprot_id, endpoint),
            timeout=self.timeout,
        )
        if resp.status_code == 404:
            return {
                "status": "error",
                "error": "Protein {} not found in iPTMnet".format(uniprot_id),
            }
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": "iPTMnet returned HTTP {}".format(resp.status_code),
            }
        return {"status": "success", "data": resp.json()}

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search proteins by name/keyword with optional role and PTM type filters."""
        search_term = (
            arguments.get("search_term")
            or arguments.get("query")
            or arguments.get("gene_symbol")
            or arguments.get("protein")
        )
        if not search_term:
            return {
                "status": "error",
                "error": "Missing required parameter: search_term",
            }

        role = arguments.get("role", "Substrate")
        ptm_type = arguments.get("ptm_type")
        term_type = arguments.get("term_type", "All")
        max_results = arguments.get("max_results", 25)

        params = {
            "search_term": search_term,
            "term_type": term_type,
            "role": role,
        }
        if ptm_type:
            params["ptm_type"] = ptm_type

        resp = self.session.get(
            "{}/search".format(IPTMNET_BASE_URL),
            params=params,
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": "iPTMnet search returned HTTP {}".format(resp.status_code),
            }

        data = resp.json()
        if not isinstance(data, list):
            return {
                "status": "error",
                "error": "Unexpected response format from iPTMnet",
            }

        results = data[:max_results]
        formatted = []
        for entry in results:
            formatted.append(
                {
                    "uniprot_id": entry.get("iptm_id", ""),
                    "uniprot_ac": entry.get("uniprot_ac", ""),
                    "protein_name": entry.get("protein_name", "").rstrip(";"),
                    "gene_name": entry.get("gene_name", ""),
                    "organism": entry.get("organism", {}).get("species", ""),
                    "substrate_role": entry.get("substrate_role", False),
                    "substrate_num": entry.get("substrate_num", 0),
                    "enzyme_role": entry.get("enzyme_role", False),
                    "enzyme_num": entry.get("enzyme_num", 0),
                    "ptm_dependent_ppi": entry.get("ptm_dependent_ppi_role", False),
                    "ptm_sites": entry.get("sites", 0),
                    "isoforms": entry.get("isoforms", 0),
                }
            )

        return {
            "status": "success",
            "data": formatted,
            "metadata": {
                "total_results": len(data),
                "returned": len(formatted),
                "search_term": search_term,
                "role_filter": role,
                "ptm_type_filter": ptm_type,
            },
        }

    def _get_ptm_sites(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get all PTM sites for a protein by UniProt accession."""
        uniprot_id = arguments.get("uniprot_id")
        if not uniprot_id:
            return {
                "status": "error",
                "error": "Missing required parameter: uniprot_id",
            }

        ptm_type_filter = arguments.get("ptm_type")

        result = self._fetch_protein_data(uniprot_id, "substrate")
        if result["status"] == "error":
            return result
        data = result["data"]
        if not isinstance(data, dict):
            return {"status": "error", "error": "Unexpected response format"}

        all_sites = []
        for isoform_id, sites in data.items():
            for site in sites:
                ptm = site.get("ptm_type")
                # Skip protein-level interaction entries that lack a specific modification site
                if not ptm and not site.get("site") and not site.get("residue"):
                    continue
                if ptm_type_filter and ptm and ptm.lower() != ptm_type_filter.lower():
                    continue
                enzymes = [
                    {"uniprot_id": e.get("id", ""), "name": e.get("name", "")}
                    for e in site.get("enzymes", [])
                    if e.get("id") or e.get("name")
                ]
                all_sites.append(
                    {
                        "isoform": isoform_id,
                        "residue": site.get("residue") or "",
                        "site": site.get("site") or "",
                        "ptm_type": ptm or "",
                        "score": site.get("score"),
                        "sources": [s.get("name", "") for s in site.get("sources", [])],
                        "enzymes": enzymes,
                        "pmids": site.get("pmids", []),
                    }
                )

        ptm_summary = {}
        for s in all_sites:
            t = s["ptm_type"] or "Unknown"
            ptm_summary[t] = ptm_summary.get(t, 0) + 1

        return {
            "status": "success",
            "data": all_sites,
            "metadata": {
                "uniprot_id": uniprot_id,
                "total_sites": len(all_sites),
                "isoforms": list(data.keys()),
                "ptm_type_summary": ptm_summary,
            },
        }

    def _get_proteoforms(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get proteoform records for a protein."""
        uniprot_id = arguments.get("uniprot_id")
        if not uniprot_id:
            return {
                "status": "error",
                "error": "Missing required parameter: uniprot_id",
            }

        result = self._fetch_protein_data(uniprot_id, "proteoforms")
        if result["status"] == "error":
            return result
        data = result["data"]
        if not isinstance(data, list):
            return {"status": "error", "error": "Unexpected response format"}

        formatted = []
        for entry in data:
            enzyme = entry.get("ptm_enzyme", {})
            formatted.append(
                {
                    "pro_id": entry.get("pro_id", ""),
                    "label": entry.get("label", ""),
                    "sites": entry.get("sites", []),
                    "enzyme_pro_id": enzyme.get("pro_id", ""),
                    "enzyme_label": enzyme.get("label", ""),
                    "source": entry.get("source", {}).get("name", ""),
                    "pmids": entry.get("pmids", []),
                }
            )

        return {
            "status": "success",
            "data": formatted,
            "metadata": {
                "uniprot_id": uniprot_id,
                "total_proteoforms": len(formatted),
            },
        }

    def _get_ptm_ppi(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get PTM-dependent protein-protein interactions."""
        uniprot_id = arguments.get("uniprot_id")
        if not uniprot_id:
            return {
                "status": "error",
                "error": "Missing required parameter: uniprot_id",
            }

        ptm_type_filter = arguments.get("ptm_type")

        result = self._fetch_protein_data(uniprot_id, "ptmppi")
        if result["status"] == "error":
            return result
        data = result["data"]
        if not isinstance(data, list):
            return {"status": "error", "error": "Unexpected response format"}

        results = []
        for entry in data:
            ptm = entry.get("ptm_type", "")
            if ptm_type_filter and ptm and ptm.lower() != ptm_type_filter.lower():
                continue
            substrate = entry.get("substrate", {})
            interactant = entry.get("interactant", {})
            results.append(
                {
                    "ptm_type": ptm,
                    "substrate_uniprot_id": substrate.get("uniprot_id", ""),
                    "substrate_name": substrate.get("name", ""),
                    "site": entry.get("site", ""),
                    "interactant_uniprot_id": interactant.get("uniprot_id", ""),
                    "interactant_name": interactant.get("name", ""),
                    "association_type": entry.get("association_type", ""),
                    "source": entry.get("source", {}).get("name", ""),
                    "pmid": entry.get("pmid", ""),
                }
            )

        ptm_summary = {}
        for r in results:
            t = r["ptm_type"] or "Unknown"
            ptm_summary[t] = ptm_summary.get(t, 0) + 1

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "uniprot_id": uniprot_id,
                "total_interactions": len(results),
                "ptm_type_summary": ptm_summary,
            },
        }
