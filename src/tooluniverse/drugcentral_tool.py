# drugcentral_tool.py
"""
DrugCentral data access tool for ToolUniverse.

DrugCentral (University of New Mexico) provides open-access drug information
including targets, indications, contraindications, and regulatory approvals.
DrugCentral's own REST API is down (confirmed Feb 2026), but its data is
available through MyChem.info (BioThings) which aggregates DrugCentral data.

This tool queries MyChem.info and extracts DrugCentral-specific fields:
- bioactivity: drug targets with UniProt IDs, activity types, and values
- drug_use: indications, contraindications, and off-label uses (SNOMED/UMLS)
- approval: FDA/EMA/PMDA approval dates and sponsors
- structures: InChIKey, SMILES, CAS RN, INN name
- xrefs: cross-references to ChEMBL, DrugBank, KEGG, PubChem, RxNorm, etc.

No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

MYCHEM_BASE = "https://mychem.info/v1"

# Fields to retrieve from MyChem for DrugCentral data
DC_ALL_FIELDS = "drugcentral"
DC_TARGET_FIELDS = "drugcentral.bioactivity"
DC_USE_FIELDS = (
    "drugcentral.drug_use,drugcentral.approval,drugcentral.structures,drugcentral.xrefs"
)


@register_tool("DrugCentralTool")
class DrugCentralTool(BaseTool):
    """
    Tool for accessing DrugCentral data via MyChem.info.

    Provides drug target information, indications, contraindications,
    off-label uses, regulatory approvals, and cross-references from
    DrugCentral's curated database.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get("operation", "search")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the DrugCentral data query."""
        try:
            if self.operation == "search":
                return self._search_drugs(arguments)
            elif self.operation == "get_drug":
                return self._get_drug(arguments)
            elif self.operation == "get_targets":
                return self._get_targets(arguments)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown operation: {self.operation}",
                }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"MyChem.info request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to MyChem.info API"}
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error querying DrugCentral data: {str(e)}",
            }

    def _search_drugs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for drugs with DrugCentral data via MyChem.info."""
        query = arguments.get("query", "") or arguments.get("q", "")
        if not query:
            return {
                "status": "error",
                "error": "query parameter is required (e.g., 'metformin', 'aspirin')",
            }

        size = min(int(arguments.get("size", 10)), 50)

        # Search MyChem specifically in drugcentral fields to avoid NDC noise.
        # Try drugcentral.structures.inn first (exact drug name match), then
        # fall back to a broader drugcentral-scoped search.
        dc_fields = (
            "drugcentral.structures.inn,drugcentral.structures.cas_rn,"
            "drugcentral.structures.smiles,drugcentral.structures.inchikey,"
            "drugcentral.approval,drugcentral.xrefs"
        )
        params = {
            "q": f"drugcentral.structures.inn:{query}",
            "fields": dc_fields,
            "size": size,
        }
        response = requests.get(
            f"{MYCHEM_BASE}/query", params=params, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        # If no results from INN search, try broader drugcentral scope
        if not data.get("hits"):
            params["q"] = (
                f"drugcentral.xrefs.drugbank_id:{query} OR drugcentral.structures.cas_rn:{query}"
            )
            response = requests.get(
                f"{MYCHEM_BASE}/query", params=params, timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

        # Last resort: general text search filtered to entries with drugcentral data
        if not data.get("hits"):
            params["q"] = f"{query} AND _exists_:drugcentral"
            response = requests.get(
                f"{MYCHEM_BASE}/query", params=params, timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

        hits = data.get("hits", [])
        results = []
        seen_inchikeys = set()
        for hit in hits:
            dc = hit.get("drugcentral", {})
            if not dc:
                continue
            structures = dc.get("structures", {})
            inchikey = structures.get("inchikey") or hit.get("_id", "")
            if inchikey in seen_inchikeys:
                continue
            seen_inchikeys.add(inchikey)
            xrefs = dc.get("xrefs", {})
            results.append(
                {
                    "inchikey": inchikey,
                    "name": structures.get("inn"),
                    "cas_rn": structures.get("cas_rn"),
                    "smiles": structures.get("smiles"),
                    "approval": dc.get("approval"),
                    "drugbank_id": xrefs.get("drugbank_id"),
                    "chembl_id": xrefs.get("chembl_id"),
                    "pubchem_cid": xrefs.get("pubchem_cid"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "total_hits": data.get("total", 0),
                "returned": len(results),
                "query": query,
                "source": "DrugCentral via MyChem.info",
            },
        }

    def _resolve_name_to_id(self, name: str) -> str:
        """Resolve drug name to MyChem.info ID via search."""
        resp = requests.get(
            f"{MYCHEM_BASE}/query",
            params={
                "q": f'drugcentral.structures.inn:"{name}"',
                "fields": "_id",
                "size": 1,
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        return hits[0]["_id"] if hits else ""

    def _get_drug(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed DrugCentral data for a drug by InChIKey, ChEMBL ID, or drug name."""
        chem_id = (
            arguments.get("chem_id", "")
            or arguments.get("inchikey", "")
            or arguments.get("drug_name", "")
        )
        if not chem_id:
            return {
                "status": "error",
                "error": "chem_id parameter is required (InChIKey, ChEMBL ID, or drug name).",
            }
        # If it looks like a drug name (no special chars), resolve to ID first
        if chem_id.isalpha() or " " in chem_id:
            resolved = self._resolve_name_to_id(chem_id)
            if resolved:
                chem_id = resolved
            # else try as-is

        params = {"fields": DC_ALL_FIELDS}
        response = requests.get(
            f"{MYCHEM_BASE}/chem/{chem_id}", params=params, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        dc = data.get("drugcentral", {})
        if not dc:
            return {
                "status": "error",
                "error": f"No DrugCentral data found for '{chem_id}'. Try using InChIKey format.",
            }

        structures = dc.get("structures", {})
        drug_use = dc.get("drug_use", {})
        indications = (
            drug_use.get("indication", []) if isinstance(drug_use, dict) else []
        )
        contras = (
            drug_use.get("contraindication", []) if isinstance(drug_use, dict) else []
        )
        off_label = (
            drug_use.get("off_label_use", []) if isinstance(drug_use, dict) else []
        )

        return {
            "status": "success",
            "data": {
                "inchikey": data.get("_id"),
                "name": structures.get("inn"),
                "cas_rn": structures.get("cas_rn"),
                "smiles": structures.get("smiles"),
                "approval": dc.get("approval", []),
                "indications": [
                    {
                        "name": i.get("concept_name"),
                        "snomed_id": i.get("snomed_concept_id"),
                        "umls_cui": i.get("umls_cui"),
                    }
                    for i in (
                        indications if isinstance(indications, list) else [indications]
                    )
                ],
                "contraindications": [
                    {
                        "name": c.get("concept_name"),
                        "snomed_id": c.get("snomed_concept_id"),
                        "umls_cui": c.get("umls_cui"),
                    }
                    for c in (contras if isinstance(contras, list) else [contras])
                ],
                "off_label_uses": [
                    {
                        "name": o.get("concept_name"),
                        "snomed_id": o.get("snomed_concept_id"),
                        "umls_cui": o.get("umls_cui"),
                    }
                    for o in (off_label if isinstance(off_label, list) else [off_label])
                ],
                "cross_references": dc.get("xrefs", {}),
            },
            "metadata": {
                "query_id": chem_id,
                "source": "DrugCentral via MyChem.info",
            },
        }

    def _get_targets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get drug targets from DrugCentral bioactivity data."""
        chem_id = (
            arguments.get("chem_id", "")
            or arguments.get("inchikey", "")
            or arguments.get("drug_name", "")
        )
        if chem_id and (chem_id.isalpha() or " " in chem_id):
            resolved = self._resolve_name_to_id(chem_id)
            if resolved:
                chem_id = resolved
        if not chem_id:
            return {
                "status": "error",
                "error": "chem_id parameter is required. Use InChIKey (e.g., 'XZWYZXLIPXDOLR-UHFFFAOYSA-N' for metformin) "
                "or ChEMBL ID (e.g., 'CHEMBL1431').",
            }

        params = {"fields": "drugcentral.bioactivity,drugcentral.structures.inn"}
        response = requests.get(
            f"{MYCHEM_BASE}/chem/{chem_id}", params=params, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        dc = data.get("drugcentral", {})
        if not dc:
            return {
                "status": "error",
                "error": f"No DrugCentral data found for '{chem_id}'. Try using InChIKey format.",
            }

        bioactivity = dc.get("bioactivity", [])
        if not isinstance(bioactivity, list):
            bioactivity = [bioactivity]

        drug_name = dc.get("structures", {}).get("inn")
        targets = []
        for ba in bioactivity:
            uniprot_info = ba.get("uniprot", [])
            if not isinstance(uniprot_info, list):
                uniprot_info = [uniprot_info]
            uniprot_ids = [
                u.get("uniprot_id") for u in uniprot_info if u.get("uniprot_id")
            ]
            gene_symbols = [
                u.get("gene_symbol") for u in uniprot_info if u.get("gene_symbol")
            ]
            targets.append(
                {
                    "target_name": ba.get("target_name"),
                    "target_class": ba.get("target_class"),
                    "organism": ba.get("organism"),
                    "action_type": ba.get("action_type"),
                    "activity_type": ba.get("act_type"),
                    "activity_value": ba.get("act_value"),
                    "is_moa": ba.get("moa") == "1",
                    "source": ba.get("act_source"),
                    "uniprot_ids": uniprot_ids,
                    "gene_symbols": gene_symbols,
                }
            )

        return {
            "status": "success",
            "data": {
                "drug_name": drug_name,
                "targets": targets,
            },
            "metadata": {
                "total_targets": len(targets),
                "query_id": chem_id,
                "source": "DrugCentral via MyChem.info",
            },
        }
