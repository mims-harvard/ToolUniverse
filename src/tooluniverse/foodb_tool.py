"""
FooDB tool for ToolUniverse — food chemical-constituent database.

FooDB is the largest database of food constituents/chemicals (the molecules that
make up food, including phytochemicals and metabolites), complementary to nutrient
databases like USDA FoodData Central. This tool retrieves a food compound by its
FooDB id (FDB...), returning structure, properties, food-occurrence description, and
cross-references (HMDB, KEGG, PubChem, ChEBI) for ID bridging in food/metabolomics work.

API: https://foodb.ca/compounds/{FDB_id}.json  (public, no authentication, JSON)
Note: FooDB has no working name-search API; look up by FDB compound id.
"""

from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

FOODB_BASE = "https://foodb.ca/compounds"


@register_tool("FooDBCompoundTool")
class FooDBCompoundTool(BaseTool):
    """Get a FooDB food-constituent compound by its FooDB id (FDB...)."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        fdb_id = (arguments.get("fdb_id") or "").strip().upper()
        if not fdb_id:
            return {
                "status": "error",
                "error": "'fdb_id' is required (a FooDB compound id, e.g. 'FDB000004')",
            }

        try:
            resp = requests.get(
                f"{FOODB_BASE}/{fdb_id}.json",
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
            if resp.status_code == 404:
                return {
                    "status": "success",
                    "data": {},
                    "metadata": {
                        "query_fdb_id": fdb_id,
                        "note": f"No FooDB compound '{fdb_id}'.",
                    },
                }
            resp.raise_for_status()
            c = resp.json()
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"FooDB request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"FooDB request failed: {e}"}
        except ValueError:
            return {"status": "error", "error": "FooDB returned a non-JSON response"}

        if not isinstance(c, dict) or not c.get("public_id"):
            return {
                "status": "success",
                "data": {},
                "metadata": {"query_fdb_id": fdb_id},
            }

        return {
            "status": "success",
            "data": {
                "fdb_id": c.get("public_id"),
                "name": c.get("name"),
                "description": c.get("description"),
                "cas_number": c.get("cas_number"),
                "formula": c.get("moldb_formula"),
                "smiles": c.get("moldb_smiles"),
                "inchi": c.get("moldb_inchi"),
                "inchikey": c.get("moldb_inchikey"),
                "logp": c.get("moldb_logp") or c.get("moldb_alogps_logp"),
                "solubility": c.get("moldb_alogps_solubility")
                or c.get("experimental_solubility"),
                "annotation_quality": c.get("annotation_quality"),
                "cross_references": {
                    "hmdb_id": c.get("hmdb_id"),
                    "kegg_compound_id": c.get("kegg_compound_id"),
                    "pubchem_compound_id": c.get("pubchem_compound_id"),
                    "chebi_id": c.get("chebi_id"),
                },
            },
            "metadata": {"query_fdb_id": fdb_id, "source": "FooDB"},
        }
