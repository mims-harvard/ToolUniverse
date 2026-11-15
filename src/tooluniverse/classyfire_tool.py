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


ALTERNATIVE_PARENTS = 50
CHEBI_TERMS = 50


def _node(node: Any) -> Optional[dict]:
    """A ChemOnt taxonomy node with the identifier that makes it citable.

    ClassyFire ships every node as {name, description, chemont_id, url}.
    Keeping only the name turns "Benzene and substituted derivatives" into
    prose: nothing downstream can join it to ChemOnt, and two tools cannot
    agree that they mean CHEMONTID:0002279. The name fields are left as
    they were so existing callers keep working; this adds the rest.
    """
    if not isinstance(node, dict) or not node.get("name"):
        return None
    return {
        "name": node.get("name"),
        "chemont_id": node.get("chemont_id"),
        "url": node.get("url"),
        "description": node.get("description"),
    }


def _nodes(rows, limit=None) -> list:
    out = [_node(n) for n in (rows or [])]
    out = [n for n in out if n]
    return out[:limit] if limit else out


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
                # The same taxonomy as above, with each level's ChemOnt id
                # and URL. For aspirin the class is CHEMONTID:0002279.
                "taxonomy": [
                    dict(node, level=level)
                    for level, node in (
                        ("kingdom", _node(rec.get("kingdom"))),
                        ("superclass", _node(rec.get("superclass"))),
                        ("class", _node(rec.get("class"))),
                        ("subclass", _node(rec.get("subclass"))),
                        ("direct_parent", _node(rec.get("direct_parent"))),
                    )
                    if node
                ],
                "intermediate_node_details": _nodes(
                    rec.get("intermediate_nodes")
                ),
                # ClassyFire's other valid classifications for the same
                # structure. Aspirin is a phenol ester and a benzoic acid as
                # well as a substituted benzene, and only the last reached
                # the caller.
                "alternative_parents": _nodes(
                    rec.get("alternative_parents"), ALTERNATIVE_PARENTS
                ),
                "alternative_parent_count": len(
                    rec.get("alternative_parents") or []
                ),
                # Mappings out of ChemOnt into vocabularies a caller is more
                # likely to already hold.
                "predicted_chebi_terms": (
                    rec.get("predicted_chebi_terms") or []
                )[:CHEBI_TERMS],
                "predicted_chebi_term_count": len(
                    rec.get("predicted_chebi_terms") or []
                ),
                "predicted_lipidmaps_terms": (
                    rec.get("predicted_lipidmaps_terms") or []
                ),
                # The curated annotations the source databases already carry
                # for this structure: for aspirin, CHEBI:15365 with
                # "salicylates", "acetate ester", "benzoic acids".
                "external_descriptors": [
                    {
                        "source": row.get("source"),
                        "source_id": row.get("source_id"),
                        "annotations": row.get("annotations") or [],
                    }
                    for row in (rec.get("external_descriptors") or [])
                    if isinstance(row, dict)
                ],
                "ancestors": rec.get("ancestors") or [],
                "smiles": rec.get("smiles"),
                # Which ChemOnt release produced this classification.
                "classification_version": rec.get("classification_version"),
            },
            "metadata": {"classified": True, "source": "ClassyFire (ChemOnt)"},
        }
