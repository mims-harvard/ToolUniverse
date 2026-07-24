"""
ClassyFire tool for ToolUniverse — automated chemical taxonomy by InChIKey.

ClassyFire (Wishart Lab) assigns a structure to a hierarchical chemical ontology
(ChemOnt): kingdom -> superclass -> class -> subclass -> direct parent, plus the
molecular framework, substituents, and a textual description. This wraps the
precomputed InChIKey lookup, which is an instant cache hit for known structures.

API: http://classyfire.wishartlab.com/entities/{inchikey}.json (public, no auth)
"""

from typing import Any, Dict, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

CLASSYFIRE_BASE = "http://classyfire.wishartlab.com/entities"


def _name(node: Any) -> Optional[str]:
    """ChemOnt nodes are {'name', 'chemont_id', ...}; pull the name."""
    return node.get("name") if isinstance(node, dict) else node


@register_tool("ClassyFireTool")
class ClassyFireTool(BaseTool):
    """Classify a chemical structure into the ChemOnt taxonomy by InChIKey."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        inchikey = (arguments.get("inchikey") or "").strip()
        if not inchikey:
            return {
                "status": "error",
                "error": "'inchikey' is required (a full 27-char InChIKey, e.g. 'BSYNRYMUTXBXSQ-UHFFFAOYSA-N')",
            }

        url = f"{CLASSYFIRE_BASE}/{inchikey}.json"
        try:
            resp = requests.get(
                url, headers={"Accept": "application/json"}, timeout=self.timeout
            )
            if resp.status_code == 404:
                return {
                    "status": "success",
                    "data": {"inchikey": inchikey, "classified": False},
                    "metadata": {
                        "classified": False,
                        "note": f"InChIKey '{inchikey}' is not in the ClassyFire cache. "
                        "Only previously-classified structures are available via this lookup.",
                        "source": "ClassyFire",
                    },
                }
            resp.raise_for_status()
            rec = resp.json()
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"ClassyFire request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"ClassyFire request failed: {e}"}
        except ValueError:
            return {
                "status": "error",
                "error": "ClassyFire returned a non-JSON response",
            }

        # A cache miss can also come back as 200 with an empty/no-taxonomy body.
        if not isinstance(rec, dict) or not rec.get("kingdom"):
            return {
                "status": "success",
                "data": {"inchikey": inchikey, "classified": False},
                "metadata": {"classified": False, "source": "ClassyFire"},
            }

        return {
            "status": "success",
            "data": {
                "inchikey": rec.get("inchikey") or inchikey,
                "classified": True,
                "kingdom": _name(rec.get("kingdom")),
                "superclass": _name(rec.get("superclass")),
                "class": _name(rec.get("class")),
                "subclass": _name(rec.get("subclass")),
                "direct_parent": _name(rec.get("direct_parent")),
                "intermediate_nodes": [
                    _name(n) for n in rec.get("intermediate_nodes", [])
                ],
                "molecular_framework": rec.get("molecular_framework"),
                "substituents": rec.get("substituents", []),
                "description": rec.get("description"),
            },
            "metadata": {"classified": True, "source": "ClassyFire (ChemOnt)"},
        }
