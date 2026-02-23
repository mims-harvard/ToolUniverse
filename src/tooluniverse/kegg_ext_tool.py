# kegg_ext_tool.py
"""
KEGG Extended API tool for ToolUniverse.

Provides access to additional KEGG REST API endpoints for gene-pathway links,
pathway gene lists, and compound/metabolite information. Complements the
existing KEGG tools (search, gene info, pathway info, list organisms).

API: https://rest.kegg.jp/
No authentication required. Free public access.
Note: KEGG REST returns tab-separated text, not JSON. This tool parses
the text into structured JSON responses.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool


KEGG_BASE_URL = "https://rest.kegg.jp"


class KEGGExtTool(BaseTool):
    """
    Tool for KEGG REST API extended endpoints providing gene-pathway links,
    pathway gene lists, and compound details.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_gene_pathways")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the KEGG API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"KEGG API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to KEGG REST API"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            if code == 404:
                return {"error": f"KEGG entry not found"}
            return {"error": f"KEGG API HTTP error: {code}"}
        except Exception as e:
            return {"error": f"Unexpected error querying KEGG: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "get_gene_pathways":
            return self._get_gene_pathways(arguments)
        elif self.endpoint == "get_pathway_genes":
            return self._get_pathway_genes(arguments)
        elif self.endpoint == "get_compound":
            return self._get_compound(arguments)
        elif self.endpoint == "list_brite":
            return self._list_brite(arguments)
        elif self.endpoint == "get_brite_hierarchy":
            return self._get_brite_hierarchy(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_gene_pathways(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get all KEGG pathways that a gene participates in."""
        gene_id = arguments.get("gene_id", "")
        if not gene_id:
            return {"error": "gene_id is required (e.g., 'hsa:7157' for human TP53)"}

        # Ensure proper KEGG format (org:id)
        if ":" not in gene_id:
            return {
                "error": "gene_id must be in KEGG format 'organism:id' (e.g., 'hsa:7157')"
            }

        # Get pathway links
        url = f"{KEGG_BASE_URL}/link/pathway/{gene_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        pathways = []
        for line in response.text.strip().split("\n"):
            if line.strip():
                parts = line.strip().split("\t")
                if len(parts) >= 2:
                    pathways.append(parts[1])

        if not pathways:
            return {
                "data": {
                    "gene_id": gene_id,
                    "pathway_count": 0,
                    "pathways": [],
                },
                "metadata": {"source": "KEGG REST API", "gene_id": gene_id},
            }

        # Get pathway names
        pathway_details = []
        for pw_id in pathways:
            pathway_details.append({"pathway_id": pw_id})

        # Batch get pathway names via list
        org = gene_id.split(":")[0]
        list_url = f"{KEGG_BASE_URL}/list/pathway/{org}"
        list_response = requests.get(list_url, timeout=self.timeout)

        if list_response.status_code == 200:
            pw_names = {}
            for line in list_response.text.strip().split("\n"):
                if line.strip():
                    parts = line.strip().split("\t")
                    if len(parts) >= 2:
                        pw_names[parts[0]] = parts[1]

            for pd in pathway_details:
                # Map path:hsaXXXXX format
                pw_id = pd["pathway_id"]
                name = pw_names.get(pw_id, "")
                if not name:
                    # Try without path: prefix
                    short_id = pw_id.replace("path:", "")
                    name = pw_names.get(short_id, "")
                pd["pathway_name"] = name

        return {
            "data": {
                "gene_id": gene_id,
                "pathway_count": len(pathway_details),
                "pathways": pathway_details,
            },
            "metadata": {
                "source": "KEGG REST API",
                "gene_id": gene_id,
            },
        }

    def _get_pathway_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get all genes in a KEGG pathway."""
        pathway_id = arguments.get("pathway_id", "")
        if not pathway_id:
            return {
                "error": "pathway_id is required (e.g., 'hsa04115' for p53 signaling)"
            }

        # Determine organism prefix from pathway ID
        # hsa04115 -> hsa
        org = ""
        for i, ch in enumerate(pathway_id):
            if ch.isdigit():
                org = pathway_id[:i]
                break

        if not org:
            return {
                "error": "Cannot determine organism from pathway_id. Use format like 'hsa04115'"
            }

        # Get gene links for pathway
        url = f"{KEGG_BASE_URL}/link/{org}/{pathway_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        genes = []
        for line in response.text.strip().split("\n"):
            if line.strip():
                parts = line.strip().split("\t")
                if len(parts) >= 2:
                    genes.append(parts[1])

        # Get pathway name
        pw_name = ""
        info_url = f"{KEGG_BASE_URL}/list/pathway/{org}"
        info_response = requests.get(info_url, timeout=self.timeout)
        if info_response.status_code == 200:
            for line in info_response.text.strip().split("\n"):
                if pathway_id in line:
                    parts = line.strip().split("\t")
                    if len(parts) >= 2:
                        pw_name = parts[1]
                    break

        return {
            "data": {
                "pathway_id": pathway_id,
                "pathway_name": pw_name,
                "gene_count": len(genes),
                "genes": genes,
            },
            "metadata": {
                "source": "KEGG REST API",
                "pathway_id": pathway_id,
                "organism": org,
            },
        }

    def _get_compound(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get KEGG compound/metabolite details."""
        compound_id = arguments.get("compound_id", "")
        if not compound_id:
            return {"error": "compound_id is required (e.g., 'C00002' for ATP)"}

        # Ensure proper KEGG compound format
        if not compound_id.startswith("C"):
            compound_id = f"C{compound_id}"

        url = f"{KEGG_BASE_URL}/get/{compound_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        text = response.text
        if not text.strip():
            return {"error": f"Compound not found: {compound_id}"}

        # Parse KEGG flat file format
        result = {
            "compound_id": compound_id,
            "names": [],
            "formula": None,
            "exact_mass": None,
            "mol_weight": None,
            "pathways": {},
            "enzymes": [],
            "dblinks": {},
        }

        current_field = None
        for line in text.split("\n"):
            if line.startswith("NAME"):
                current_field = "NAME"
                name = line[12:].strip().rstrip(";")
                if name:
                    result["names"].append(name)
            elif line.startswith("FORMULA"):
                result["formula"] = line[12:].strip()
                current_field = None
            elif line.startswith("EXACT_MASS"):
                try:
                    result["exact_mass"] = float(line[12:].strip())
                except ValueError:
                    result["exact_mass"] = line[12:].strip()
                current_field = None
            elif line.startswith("MOL_WEIGHT"):
                try:
                    result["mol_weight"] = float(line[12:].strip())
                except ValueError:
                    result["mol_weight"] = line[12:].strip()
                current_field = None
            elif line.startswith("PATHWAY"):
                current_field = "PATHWAY"
                parts = line[12:].strip().split("  ", 1)
                if len(parts) >= 2:
                    result["pathways"][parts[0].strip()] = parts[1].strip()
                elif parts:
                    result["pathways"][parts[0].strip()] = ""
            elif line.startswith("ENZYME"):
                current_field = "ENZYME"
                enzymes = line[12:].strip().split()
                result["enzymes"].extend(enzymes)
            elif line.startswith("DBLINKS"):
                current_field = "DBLINKS"
                parts = line[12:].strip().split(": ", 1)
                if len(parts) == 2:
                    result["dblinks"][parts[0].strip()] = parts[1].strip()
            elif line.startswith("REMARK"):
                result["remark"] = line[12:].strip()
                current_field = None
            elif line.startswith("///"):
                break
            elif line.startswith("            "):
                content = line[12:].strip()
                if current_field == "NAME":
                    name = content.rstrip(";")
                    if name:
                        result["names"].append(name)
                elif current_field == "PATHWAY":
                    parts = content.split("  ", 1)
                    if len(parts) >= 2:
                        result["pathways"][parts[0].strip()] = parts[1].strip()
                elif current_field == "ENZYME":
                    result["enzymes"].extend(content.split())
                elif current_field == "DBLINKS":
                    parts = content.split(": ", 1)
                    if len(parts) == 2:
                        result["dblinks"][parts[0].strip()] = parts[1].strip()
            else:
                # New field we don't specifically handle
                current_field = None

        return {
            "data": result,
            "metadata": {
                "source": "KEGG REST API",
                "compound_id": compound_id,
            },
        }

    def _list_brite(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all available KEGG BRITE hierarchy classifications."""
        url = f"{KEGG_BASE_URL}/list/brite"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        hierarchies = []
        for line in response.text.strip().split("\n"):
            if line.strip():
                parts = line.strip().split("\t", 1)
                if len(parts) >= 2:
                    hierarchies.append(
                        {
                            "hierarchy_id": parts[0].strip(),
                            "name": parts[1].strip(),
                        }
                    )
                elif parts:
                    hierarchies.append(
                        {
                            "hierarchy_id": parts[0].strip(),
                            "name": "",
                        }
                    )

        return {
            "data": {
                "hierarchy_count": len(hierarchies),
                "hierarchies": hierarchies,
            },
            "metadata": {
                "source": "KEGG BRITE",
            },
        }

    def _get_brite_hierarchy(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific KEGG BRITE hierarchy as a JSON tree."""
        hierarchy_id = arguments.get("hierarchy_id", "")
        if not hierarchy_id:
            return {"error": "hierarchy_id is required (e.g., 'ko01000' for Enzymes)"}

        # KEGG BRITE JSON endpoint requires br: prefix
        url = f"{KEGG_BASE_URL}/get/br:{hierarchy_id}/json"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        if not response.text.strip():
            return {"error": f"BRITE hierarchy not found: {hierarchy_id}"}

        tree = response.json()

        return {
            "data": tree,
            "metadata": {
                "source": "KEGG BRITE",
                "hierarchy_id": hierarchy_id,
            },
        }
