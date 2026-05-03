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


def _parse_tsv_column(text: str, column: int = 0) -> list:
    """Extract a single column from KEGG tab-separated text output."""
    results = []
    for line in text.strip().split("\n"):
        parts = line.strip().split("\t")
        if len(parts) > column:
            results.append(parts[column])
    return results


def _fetch_pathway_names(organism: str, timeout: int) -> Dict[str, str]:
    """Fetch pathway_id → pathway_name mapping for an organism."""
    url = f"{KEGG_BASE_URL}/list/pathway/{organism}"
    resp = requests.get(url, timeout=timeout)
    if resp.status_code != 200:
        return {}
    pw_names = {}
    for line in resp.text.strip().split("\n"):
        parts = line.strip().split("\t")
        if len(parts) >= 2:
            pw_names[parts[0]] = parts[1]
    return pw_names


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
            return {
                "status": "error",
                "error": f"KEGG API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to KEGG REST API"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            if code == 404:
                return {"status": "error", "error": f"KEGG entry not found"}
            return {"status": "error", "error": f"KEGG API HTTP error: {code}"}
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying KEGG: {str(e)}",
            }

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
        elif self.endpoint == "search_disease":
            return self._search_disease(arguments)
        elif self.endpoint == "get_disease":
            return self._get_disease(arguments)
        elif self.endpoint == "get_disease_genes":
            return self._get_disease_genes(arguments)
        elif self.endpoint == "search_drug":
            return self._search_drug(arguments)
        elif self.endpoint == "get_drug":
            return self._get_drug(arguments)
        elif self.endpoint == "get_drug_targets":
            return self._get_drug_targets(arguments)
        elif self.endpoint == "search_network":
            return self._search_network(arguments)
        elif self.endpoint == "get_network":
            return self._get_network(arguments)
        elif self.endpoint == "search_variant":
            return self._search_variant(arguments)
        elif self.endpoint == "get_variant":
            return self._get_variant(arguments)
        elif self.endpoint == "conv_ids":
            return self._conv_ids(arguments)
        elif self.endpoint == "link_entries":
            return self._link_entries(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _resolve_gene_symbol(self, symbol: str, organism: str = "hsa") -> str:
        """Resolve gene symbol (e.g. TP53) to KEGG gene ID (e.g. hsa:7157).

        Parses /find results and matches by exact gene symbol (case-insensitive).
        """
        url = f"{KEGG_BASE_URL}/find/{organism}/{symbol}"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code != 200 or not resp.text.strip():
            return ""
        symbol_upper = symbol.upper()
        for line in resp.text.strip().split("\n"):
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            kegg_id = parts[0].strip()
            # Format: "SYMBOL1, SYN2, SYN3; description"
            annotation = parts[1].split(";")[0]
            symbols = [s.strip().upper() for s in annotation.split(",")]
            if symbol_upper in symbols:
                return kegg_id
        return ""

    def _get_gene_pathways(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get all KEGG pathways that a gene participates in."""
        gene_id = (
            arguments.get("gene_id")
            or arguments.get("gene_symbol")
            or arguments.get("gene")
            or ""
        )
        if not gene_id:
            return {
                "status": "error",
                "error": "gene_id is required (e.g., 'hsa:7157' for human TP53). You may also pass gene_symbol='TP53'.",
            }

        # Auto-resolve gene symbol to KEGG ID (e.g. TP53 → hsa:7157)
        organism = arguments.get("organism", "hsa")
        if ":" not in gene_id:
            resolved = self._resolve_gene_symbol(gene_id, organism)
            if not resolved:
                return {
                    "status": "error",
                    "error": f"Could not resolve gene symbol '{gene_id}' to a KEGG gene ID for organism '{organism}'. Use KEGG format 'hsa:7157' directly, or verify the gene symbol.",
                }
            gene_id = resolved

        # Get pathway links for this gene
        url = f"{KEGG_BASE_URL}/link/pathway/{gene_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        pathway_ids = _parse_tsv_column(response.text, column=1)

        if not pathway_ids:
            return {
                "status": "success",
                "data": {
                    "gene_id": gene_id,
                    "pathway_count": 0,
                    "pathways": [],
                },
                "metadata": {"source": "KEGG REST API", "gene_id": gene_id},
            }

        # Batch-fetch pathway names for this organism
        org = gene_id.split(":")[0]
        pw_names = _fetch_pathway_names(org, self.timeout)

        pathway_details = []
        for pw_id in pathway_ids:
            name = pw_names.get(pw_id) or pw_names.get(pw_id.replace("path:", ""), "")
            pathway_details.append({"pathway_id": pw_id, "pathway_name": name})

        return {
            "status": "success",
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
                "status": "error",
                "error": "pathway_id is required (e.g., 'hsa04115' for p53 signaling)",
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
                "status": "error",
                "error": "Cannot determine organism from pathway_id. Use format like 'hsa04115'",
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
            "status": "success",
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
            return {
                "status": "error",
                "error": "compound_id is required (e.g., 'C00002' for ATP)",
            }

        # Ensure proper KEGG compound format
        if not compound_id.startswith("C"):
            compound_id = f"C{compound_id}"

        url = f"{KEGG_BASE_URL}/get/{compound_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        text = response.text
        if not text.strip():
            return {"status": "error", "error": f"Compound not found: {compound_id}"}

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
            "status": "success",
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
            "status": "success",
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
            return {
                "status": "error",
                "error": "hierarchy_id is required (e.g., 'ko01000' for Enzymes)",
            }

        # KEGG BRITE JSON endpoint requires br: prefix
        url = f"{KEGG_BASE_URL}/get/br:{hierarchy_id}/json"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        if not response.text.strip():
            return {
                "status": "error",
                "error": f"BRITE hierarchy not found: {hierarchy_id}",
            }

        tree = response.json()

        return {
            "status": "success",
            "data": tree,
            "metadata": {
                "source": "KEGG BRITE",
                "hierarchy_id": hierarchy_id,
            },
        }

    # --- KEGG Disease endpoints ---

    def _search_disease(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search KEGG disease database by keyword."""
        keyword = arguments.get("keyword") or arguments.get("query", "")
        if not keyword:
            return {
                "status": "error",
                "error": "keyword or query is required (e.g., 'leukemia', 'diabetes')",
            }

        url = f"{KEGG_BASE_URL}/find/disease/{keyword}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        diseases = []
        for line in response.text.strip().split("\n"):
            if line.strip():
                parts = line.strip().split("\t", 1)
                if len(parts) >= 2:
                    disease_id = parts[0].strip().replace("ds:", "")
                    diseases.append(
                        {"disease_id": disease_id, "name": parts[1].strip()}
                    )

        max_results = arguments.get("max_results", 25)
        diseases = diseases[:max_results]

        return {
            "status": "success",
            "data": diseases,
            "metadata": {
                "source": "KEGG Disease",
                "keyword": keyword,
                "total": len(diseases),
            },
        }

    def _get_disease(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed KEGG disease information."""
        disease_id = arguments.get("disease_id", "")
        if not disease_id:
            return {
                "status": "error",
                "error": "disease_id is required (e.g., 'H00001')",
            }

        url = f"{KEGG_BASE_URL}/get/{disease_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        text = response.text
        if not text.strip():
            return {"status": "error", "error": f"Disease not found: {disease_id}"}

        result = {
            "disease_id": disease_id,
            "names": [],
            "category": None,
            "description": None,
            "genes": [],
            "pathways": {},
            "drugs": [],
            "dblinks": {},
            "references": [],
        }

        current_field = None
        for line in text.split("\n"):
            if line.startswith("NAME"):
                current_field = "NAME"
                name = line[12:].strip().rstrip(";")
                if name:
                    result["names"].append(name)
            elif line.startswith("DESCRIPTION"):
                current_field = "DESCRIPTION"
                result["description"] = line[12:].strip()
            elif line.startswith("CATEGORY"):
                result["category"] = line[12:].strip()
                current_field = None
            elif line.startswith("GENE"):
                current_field = "GENE"
                gene_line = line[12:].strip()
                if gene_line:
                    result["genes"].append(gene_line)
            elif line.startswith("PATHWAY"):
                current_field = "PATHWAY"
                parts = line[12:].strip().split("  ", 1)
                if len(parts) >= 2:
                    result["pathways"][parts[0].strip()] = parts[1].strip()
            elif line.startswith("DRUG"):
                current_field = "DRUG"
                drug_line = line[12:].strip()
                if drug_line:
                    result["drugs"].append(drug_line)
            elif line.startswith("DBLINKS"):
                current_field = "DBLINKS"
                parts = line[12:].strip().split(": ", 1)
                if len(parts) == 2:
                    result["dblinks"][parts[0].strip()] = parts[1].strip()
            elif line.startswith("REFERENCE"):
                current_field = "REFERENCE"
                ref = line[12:].strip()
                if ref:
                    result["references"].append(ref)
            elif line.startswith("///"):
                break
            elif line.startswith("            "):
                content = line[12:].strip()
                if current_field == "NAME":
                    name = content.rstrip(";")
                    if name:
                        result["names"].append(name)
                elif current_field == "DESCRIPTION":
                    result["description"] = (
                        (result["description"] or "") + " " + content
                    )
                elif current_field == "GENE":
                    result["genes"].append(content)
                elif current_field == "PATHWAY":
                    parts = content.split("  ", 1)
                    if len(parts) >= 2:
                        result["pathways"][parts[0].strip()] = parts[1].strip()
                elif current_field == "DRUG":
                    result["drugs"].append(content)
                elif current_field == "DBLINKS":
                    parts = content.split(": ", 1)
                    if len(parts) == 2:
                        result["dblinks"][parts[0].strip()] = parts[1].strip()
                elif current_field == "REFERENCE":
                    result["references"].append(content)
            else:
                current_field = None

        return {
            "status": "success",
            "data": result,
            "metadata": {"source": "KEGG Disease", "disease_id": disease_id},
        }

    def _get_disease_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get genes linked to a KEGG disease."""
        disease_id = arguments.get("disease_id", "")
        if not disease_id:
            return {
                "status": "error",
                "error": "disease_id is required (e.g., 'H00001')",
            }

        url = f"{KEGG_BASE_URL}/link/hsa/{disease_id}"
        organism = arguments.get("organism", "hsa")
        if organism != "hsa":
            url = f"{KEGG_BASE_URL}/link/{organism}/{disease_id}"

        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        genes = []
        for line in response.text.strip().split("\n"):
            if line.strip():
                parts = line.strip().split("\t")
                if len(parts) >= 2:
                    genes.append(parts[1])

        return {
            "status": "success",
            "data": {
                "disease_id": disease_id,
                "gene_count": len(genes),
                "genes": genes,
            },
            "metadata": {
                "source": "KEGG Disease",
                "disease_id": disease_id,
                "organism": organism,
            },
        }

    # --- KEGG Drug endpoints ---

    def _search_drug(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search KEGG drug database by keyword."""
        keyword = arguments.get("keyword", "")
        if not keyword:
            return {
                "status": "error",
                "error": "keyword is required (e.g., 'aspirin', 'imatinib')",
            }

        url = f"{KEGG_BASE_URL}/find/drug/{keyword}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        drugs = []
        for line in response.text.strip().split("\n"):
            if line.strip():
                parts = line.strip().split("\t", 1)
                if len(parts) >= 2:
                    drug_id = parts[0].strip().replace("dr:", "")
                    drugs.append({"drug_id": drug_id, "name": parts[1].strip()})

        max_results = arguments.get("max_results", 25)
        drugs = drugs[:max_results]

        return {
            "status": "success",
            "data": drugs,
            "metadata": {
                "source": "KEGG Drug",
                "keyword": keyword,
                "total": len(drugs),
            },
        }

    def _get_drug(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed KEGG drug information."""
        drug_id = arguments.get("drug_id", "")
        if not drug_id:
            return {
                "status": "error",
                "error": "drug_id is required (e.g., 'D00109' for aspirin)",
            }

        url = f"{KEGG_BASE_URL}/get/{drug_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        text = response.text
        if not text.strip():
            return {"status": "error", "error": f"Drug not found: {drug_id}"}

        result = {
            "drug_id": drug_id,
            "names": [],
            "formula": None,
            "exact_mass": None,
            "mol_weight": None,
            "targets": [],
            "pathways": {},
            "diseases": [],
            "dblinks": {},
            "efficacy": None,
            "product": [],
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
            elif line.startswith("TARGET"):
                current_field = "TARGET"
                target_line = line[12:].strip()
                if target_line:
                    result["targets"].append(target_line)
            elif line.startswith("PATHWAY"):
                current_field = "PATHWAY"
                parts = line[12:].strip().split("  ", 1)
                if len(parts) >= 2:
                    result["pathways"][parts[0].strip()] = parts[1].strip()
            elif line.startswith("DISEASE"):
                current_field = "DISEASE"
                disease_line = line[12:].strip()
                if disease_line:
                    result["diseases"].append(disease_line)
            elif line.startswith("DBLINKS"):
                current_field = "DBLINKS"
                parts = line[12:].strip().split(": ", 1)
                if len(parts) == 2:
                    result["dblinks"][parts[0].strip()] = parts[1].strip()
            elif line.startswith("EFFICACY"):
                current_field = "EFFICACY"
                result["efficacy"] = line[12:].strip()
            elif line.startswith("PRODUCT"):
                current_field = "PRODUCT"
                prod = line[12:].strip()
                if prod:
                    result["product"].append(prod)
            elif line.startswith("///"):
                break
            elif line.startswith("            "):
                content = line[12:].strip()
                if current_field == "NAME":
                    name = content.rstrip(";")
                    if name:
                        result["names"].append(name)
                elif current_field == "TARGET":
                    result["targets"].append(content)
                elif current_field == "PATHWAY":
                    parts = content.split("  ", 1)
                    if len(parts) >= 2:
                        result["pathways"][parts[0].strip()] = parts[1].strip()
                elif current_field == "DISEASE":
                    result["diseases"].append(content)
                elif current_field == "DBLINKS":
                    parts = content.split(": ", 1)
                    if len(parts) == 2:
                        result["dblinks"][parts[0].strip()] = parts[1].strip()
                elif current_field == "EFFICACY":
                    result["efficacy"] = (result["efficacy"] or "") + " " + content
                elif current_field == "PRODUCT":
                    result["product"].append(content)
            else:
                current_field = None

        return {
            "status": "success",
            "data": result,
            "metadata": {"source": "KEGG Drug", "drug_id": drug_id},
        }

    def _get_drug_targets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get gene targets linked to a KEGG drug."""
        drug_id = arguments.get("drug_id", "")
        if not drug_id:
            return {"status": "error", "error": "drug_id is required (e.g., 'D00109')"}

        # KEGG link: drug -> target genes
        url = f"{KEGG_BASE_URL}/link/hsa/{drug_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        targets = []
        for line in response.text.strip().split("\n"):
            if line.strip():
                parts = line.strip().split("\t")
                if len(parts) >= 2:
                    targets.append(parts[1])

        return {
            "status": "success",
            "data": {
                "drug_id": drug_id,
                "target_count": len(targets),
                "targets": targets,
            },
            "metadata": {"source": "KEGG Drug", "drug_id": drug_id},
        }

    # --- KEGG Network endpoints ---

    def _search_network(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search KEGG NETWORK database by keyword."""
        keyword = arguments.get("keyword", "")
        if not keyword:
            return {
                "status": "error",
                "error": "keyword is required (e.g., 'EGFR', 'RAS', 'p53')",
            }

        url = f"{KEGG_BASE_URL}/find/network/{keyword}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        networks = []
        for line in response.text.strip().split("\n"):
            if line.strip():
                parts = line.strip().split("\t", 1)
                if len(parts) >= 2:
                    net_id = parts[0].strip().replace("ne:", "")
                    networks.append({"network_id": net_id, "name": parts[1].strip()})

        max_results = arguments.get("max_results", 25)
        networks = networks[:max_results]

        return {
            "status": "success",
            "data": networks,
            "metadata": {
                "source": "KEGG Network",
                "keyword": keyword,
                "total": len(networks),
            },
        }

    def _get_network(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed KEGG network information."""
        network_id = arguments.get("network_id", "")
        if not network_id:
            return {
                "status": "error",
                "error": "network_id is required (e.g., 'N00001')",
            }

        url = f"{KEGG_BASE_URL}/get/{network_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        text = response.text
        if not text.strip():
            return {"status": "error", "error": f"Network not found: {network_id}"}

        result = {
            "network_id": network_id,
            "name": None,
            "definition": None,
            "expanded": None,
            "classes": [],
            "diseases": [],
            "drugs": [],
            "elements": [],
        }

        current_field = None
        for line in text.split("\n"):
            if line.startswith("NAME"):
                result["name"] = line[12:].strip()
                current_field = None
            elif line.startswith("DEFINITION"):
                current_field = "DEFINITION"
                result["definition"] = line[12:].strip()
            elif line.startswith("  EXPANDED"):
                result["expanded"] = line[12:].strip()
                current_field = None
            elif line.startswith("CLASS"):
                current_field = "CLASS"
                result["classes"].append(line[12:].strip())
            elif line.startswith("DISEASE"):
                current_field = "DISEASE"
                result["diseases"].append(line[12:].strip())
            elif line.startswith("DRUG_TARGET") or line.startswith("DRUG"):
                current_field = "DRUG"
                drug_line = line[12:].strip()
                if drug_line:
                    result["drugs"].append(drug_line)
            elif line.startswith("ELEMENT"):
                current_field = "ELEMENT"
                result["elements"].append(line[12:].strip())
            elif line.startswith("///"):
                break
            elif line.startswith("            "):
                content = line[12:].strip()
                if current_field == "CLASS":
                    result["classes"].append(content)
                elif current_field == "DISEASE":
                    result["diseases"].append(content)
                elif current_field == "DRUG":
                    result["drugs"].append(content)
                elif current_field == "ELEMENT":
                    result["elements"].append(content)
                elif current_field == "DEFINITION":
                    result["definition"] = (result["definition"] or "") + " " + content
            else:
                current_field = None

        return {
            "status": "success",
            "data": result,
            "metadata": {"source": "KEGG Network", "network_id": network_id},
        }

    # --- KEGG Variant endpoints ---

    def _search_variant(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search KEGG VARIANT database by gene name."""
        keyword = arguments.get("keyword", "")
        if not keyword:
            return {
                "status": "error",
                "error": "keyword is required (e.g., 'BRAF', 'TP53', 'EGFR')",
            }

        url = f"{KEGG_BASE_URL}/find/variant/{keyword}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        variants = []
        for line in response.text.strip().split("\n"):
            if line.strip():
                parts = line.strip().split("\t", 1)
                if len(parts) >= 2:
                    var_id = parts[0].strip().replace("hsa_var:", "")
                    variants.append(
                        {"variant_id": var_id, "description": parts[1].strip()}
                    )

        max_results = arguments.get("max_results", 25)
        variants = variants[:max_results]

        return {
            "status": "success",
            "data": variants,
            "metadata": {
                "source": "KEGG Variant",
                "keyword": keyword,
                "total": len(variants),
            },
        }

    def _get_variant(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed KEGG variant information."""
        variant_id = arguments.get("variant_id", "")
        if not variant_id:
            return {
                "status": "error",
                "error": "variant_id is required (e.g., 'hsa_var:673v1' for BRAF V600E)",
            }

        # Ensure proper KEGG format
        if not variant_id.startswith("hsa_var:"):
            variant_id = f"hsa_var:{variant_id}"

        url = f"{KEGG_BASE_URL}/get/{variant_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        text = response.text
        if not text.strip():
            return {"status": "error", "error": f"Variant not found: {variant_id}"}

        result = {
            "variant_id": variant_id,
            "name": None,
            "type": None,
            "gene": None,
            "organism": None,
            "variations": [],
            "networks": [],
            "diseases": [],
            "drugs": [],
        }

        current_field = None
        current_variation = None
        for line in text.split("\n"):
            if line.startswith("NAME"):
                result["name"] = line[12:].strip()
                current_field = None
            elif line.startswith("TYPE"):
                result["type"] = line[12:].strip()
                current_field = None
            elif line.startswith("GENE"):
                result["gene"] = line[12:].strip()
                current_field = None
            elif line.startswith("ORGANISM"):
                result["organism"] = line[12:].strip()
                current_field = None
            elif line.startswith("VARIATION"):
                current_field = "VARIATION"
                content = line[12:].strip()
                current_variation = {
                    "mutation": content,
                    "clinvar": [],
                    "dbsnp": [],
                    "cosmic": [],
                }
                result["variations"].append(current_variation)
            elif line.startswith("NETWORK"):
                current_field = "NETWORK"
                result["networks"].append(line[12:].strip())
            elif line.startswith("DISEASE"):
                current_field = "DISEASE"
                result["diseases"].append(line[12:].strip())
            elif line.startswith("DRUG_TARGET"):
                current_field = "DRUG"
                result["drugs"].append(line[12:].strip())
            elif line.startswith("///"):
                break
            elif line.startswith("            "):
                content = line[12:].strip()
                if current_field == "VARIATION" and current_variation:
                    if content.startswith("mutation "):
                        current_variation = {
                            "mutation": content.replace("mutation ", ""),
                            "clinvar": [],
                            "dbsnp": [],
                            "cosmic": [],
                        }
                        result["variations"].append(current_variation)
                    elif content.startswith("ClinVar:"):
                        current_variation["clinvar"] = content.replace(
                            "ClinVar: ", ""
                        ).split()
                    elif content.startswith("dbSNP:"):
                        current_variation["dbsnp"] = content.replace(
                            "dbSNP: ", ""
                        ).split()
                    elif content.startswith("COSM:"):
                        current_variation["cosmic"] = content.replace(
                            "COSM: ", ""
                        ).split()
                elif current_field == "NETWORK":
                    result["networks"].append(content)
                elif current_field == "DISEASE":
                    result["diseases"].append(content)
                elif current_field == "DRUG":
                    result["drugs"].append(content)
            else:
                current_field = None

        return {
            "status": "success",
            "data": result,
            "metadata": {"source": "KEGG Variant", "variant_id": variant_id},
        }

    def _conv_ids(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Convert between KEGG identifiers and external database IDs.

        The KEGG /conv endpoint maps KEGG gene IDs to/from external databases:
        ncbi-geneid, ncbi-proteinid, uniprot, chebi, pubchem.
        """
        kegg_id = arguments.get("kegg_id", "")
        target_db = arguments.get("target_db", "")
        if not kegg_id:
            return {
                "status": "error",
                "error": "kegg_id is required (e.g., 'hsa:7157' for TP53)",
            }
        if not target_db:
            return {
                "status": "error",
                "error": "target_db is required: uniprot, ncbi-geneid, ncbi-proteinid, chebi, or pubchem",
            }

        valid_dbs = {"uniprot", "ncbi-geneid", "ncbi-proteinid", "chebi", "pubchem"}
        if target_db not in valid_dbs:
            return {
                "status": "error",
                "error": f"target_db must be one of: {', '.join(sorted(valid_dbs))}",
            }

        url = f"{KEGG_BASE_URL}/conv/{target_db}/{kegg_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        text = response.text.strip()
        if not text:
            return {
                "status": "error",
                "error": f"No {target_db} mapping found for {kegg_id}",
            }

        mappings = []
        for line in text.split("\n"):
            parts = line.strip().split("\t")
            if len(parts) == 2:
                mappings.append({"kegg_id": parts[0], "external_id": parts[1]})

        return {
            "status": "success",
            "data": mappings,
            "metadata": {
                "source": "KEGG conv",
                "query_kegg_id": kegg_id,
                "target_db": target_db,
                "total": len(mappings),
            },
        }

    def _link_entries(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Find cross-references between KEGG databases.

        The KEGG /link endpoint finds entries linked between databases,
        e.g., all pathways linked to a given gene, or all drugs for a disease.
        """
        # Normalize parameter aliases
        source = arguments.get("source") or arguments.get("entry_id") or ""
        target = arguments.get("target") or arguments.get("target_db") or ""
        if not source or not target:
            return {
                "status": "error",
                "error": "Both source and target are required. "
                "source: KEGG entry ID (e.g., 'hsa:7157'). "
                "target: KEGG database name (e.g., 'pathway', 'disease', 'drug'). "
                "Note: 'gene' is not a valid target — use organism codes like 'hsa' for human genes.",
            }

        # 'gene' is not a valid KEGG database for /link endpoint
        if target.lower() == "gene":
            return {
                "status": "error",
                "error": "target='gene' is not valid for KEGG /link. "
                "Use an organism-specific database code instead, e.g., 'hsa' for human, 'mmu' for mouse. "
                "Valid targets include: pathway, disease, drug, compound, hsa, mmu.",
            }

        url = f"{KEGG_BASE_URL}/link/{target}/{source}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        text = response.text.strip()
        if not text:
            return {
                "status": "error",
                "error": f"No {target} entries linked to {source}",
            }

        links = []
        for line in text.split("\n"):
            parts = line.strip().split("\t")
            if len(parts) == 2:
                links.append({"source_id": parts[0], "target_id": parts[1]})

        return {
            "status": "success",
            "data": links,
            "metadata": {
                "source_query": source,
                "target_db": target,
                "total": len(links),
                "source": "KEGG link",
            },
        }
