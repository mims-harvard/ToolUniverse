# pubchem_bioassay_tool.py
"""
PubChem BioAssay API tool for ToolUniverse.

PubChem BioAssay stores biological screening data submitted by depositors
through the BioAssay Submission system. Contains over 1.3 million assays
covering drug screening, toxicology, and biological pathway probing.

API: https://pubchem.ncbi.nlm.nih.gov/rest/pug/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

PUBCHEM_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"


@register_tool("PubChemBioAssayTool")
class PubChemBioAssayTool(BaseTool):
    """
    Tool for querying PubChem BioAssay data.

    Access biological assay descriptions, targets, and screening results
    from PubChem. Supports searching by assay ID, target gene, or keyword.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_assay")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the PubChem BioAssay API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"PubChem BioAssay request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to PubChem API."}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"PubChem API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying PubChem BioAssay: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "get_assay":
            return self._get_assay(arguments)
        elif self.endpoint == "search_by_gene":
            return self._search_by_gene(arguments)
        elif self.endpoint == "get_assay_summary":
            return self._get_assay_summary(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _get_assay(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed description of a bioassay by its AID."""
        aid = arguments.get("aid")
        if not aid:
            return {"status": "error", "error": "aid (Assay ID) parameter is required"}

        url = f"{PUBCHEM_BASE_URL}/assay/aid/{aid}/description/JSON"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        containers = data.get("PC_AssayContainer", [])
        if not containers:
            return {"status": "error", "error": f"No assay found with AID {aid}"}

        assay = containers[0].get("assay", {}).get("descr", {})
        aid_info = assay.get("aid", {})
        source = assay.get("aid_source", {}).get("db", {})

        result = {
            "aid": aid_info.get("id"),
            "name": assay.get("name"),
            "source_name": source.get("name"),
            "description": assay.get("description", []),
            "protocol": assay.get("protocol", []),
            "comment": assay.get("comment", []),
        }

        # Extract target info if present
        targets = assay.get("target", [])
        if targets:
            result["targets"] = []
            for t in targets:
                mol_id = t.get("mol_id")
                target_entry = {
                    "name": t.get("name"),
                    "molecule_type": t.get("molecule_type"),
                }
                if mol_id:
                    target_entry["gi"] = mol_id.get("gi")
                result["targets"].append(target_entry)

        # Truncate long descriptions
        if result["description"] and len(result["description"]) > 5:
            result["description"] = result["description"][:5]
        if result["protocol"] and len(result["protocol"]) > 3:
            result["protocol"] = result["protocol"][:3]
        if result["comment"] and len(result["comment"]) > 3:
            result["comment"] = result["comment"][:3]

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "PubChem BioAssay",
                "aid": str(aid),
            },
        }

    def _search_by_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for bioassays targeting a specific gene."""
        gene_symbol = arguments.get("gene_symbol", "")
        if not gene_symbol:
            return {
                "status": "error",
                "error": "gene_symbol parameter is required (e.g., 'TP53', 'EGFR')",
            }

        url = f"{PUBCHEM_BASE_URL}/assay/target/genesymbol/{gene_symbol}/aids/JSON"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        aids_list = data.get("IdentifierList", {}).get("AID", [])

        # Limit to first 20 AIDs
        aids_truncated = aids_list[:20]

        # Get summaries for these AIDs
        results = []
        if aids_truncated:
            aids_str = ",".join(str(a) for a in aids_truncated[:5])
            try:
                summary_url = f"{PUBCHEM_BASE_URL}/assay/aid/{aids_str}/summary/JSON"
                sum_resp = requests.get(summary_url, timeout=self.timeout)
                sum_resp.raise_for_status()
                sum_data = sum_resp.json()

                for summary in sum_data.get("AssaySummaries", {}).get(
                    "AssaySummary", []
                ):
                    targets = summary.get("Target", [])
                    target_names = (
                        [t.get("Name", "") for t in targets] if targets else []
                    )
                    results.append(
                        {
                            "aid": summary.get("AID"),
                            "name": summary.get("Name"),
                            "source": summary.get("SourceName"),
                            "method": summary.get("Method"),
                            "targets": target_names,
                            "has_score": summary.get("HasScore"),
                        }
                    )
            except Exception:
                # Fallback: just return the AID list
                results = [{"aid": a} for a in aids_truncated]

        return {
            "status": "success",
            "data": {
                "total_assays": len(aids_list),
                "assays": results,
            },
            "metadata": {
                "source": "PubChem BioAssay",
                "gene_symbol": gene_symbol,
                "total_assays": len(aids_list),
                "returned": len(results),
            },
        }

    def _get_assay_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary and target information for a bioassay."""
        aid = arguments.get("aid")
        if not aid:
            return {"status": "error", "error": "aid (Assay ID) parameter is required"}

        url = f"{PUBCHEM_BASE_URL}/assay/aid/{aid}/summary/JSON"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        summaries = data.get("AssaySummaries", {}).get("AssaySummary", [])
        if not summaries:
            return {"status": "error", "error": f"No summary found for AID {aid}"}

        summary = summaries[0]
        targets = summary.get("Target", [])
        target_info = []
        for t in targets:
            target_info.append(
                {
                    "accession": t.get("Accession"),
                    "name": t.get("Name"),
                }
            )

        # Also get target gene info
        gene_info = []
        try:
            target_url = f"{PUBCHEM_BASE_URL}/assay/aid/{aid}/targets/ProteinGI,ProteinName,GeneID,GeneSymbol/JSON"
            t_resp = requests.get(target_url, timeout=self.timeout)
            t_resp.raise_for_status()
            t_data = t_resp.json()

            for info in t_data.get("InformationList", {}).get("Information", []):
                gene_symbols = info.get("GeneSymbol", [])
                gene_ids = info.get("GeneID", [])
                protein_names = info.get("ProteinName", [])
                gene_info.append(
                    {
                        "gene_symbols": gene_symbols,
                        "gene_ids": gene_ids,
                        "protein_names": protein_names,
                    }
                )
        except Exception:
            pass

        result = {
            "aid": summary.get("AID"),
            "name": summary.get("Name"),
            "source": summary.get("SourceName"),
            "source_id": summary.get("SourceID"),
            "method": summary.get("Method"),
            "has_score": summary.get("HasScore"),
            "number_of_tids": summary.get("NumberOfTIDs"),
            "targets": target_info,
            "gene_targets": gene_info,
        }

        # Include truncated description
        desc = summary.get("Description", [])
        if desc:
            result["description"] = desc[:3]

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "PubChem BioAssay",
                "aid": str(aid),
            },
        }
