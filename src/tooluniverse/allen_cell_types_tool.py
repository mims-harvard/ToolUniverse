"""
Allen Cell Types tool for ToolUniverse — single-neuron ephys/morphology specimens.

The Allen Cell Types Database catalogs individual neurons characterized by
electrophysiology, morphology, and transcriptomics (human + mouse). This wraps the
Brain-Map RMA query for ApiCellTypesSpecimenDetail. It is distinct from TU's existing
AllenBrain tools, which cover gene-expression datasets and brain structures.

API: http://api.brain-map.org/api/v2/data/query.json  (public, no authentication, RMA)
"""

from typing import Any, Dict, List, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

BRAINMAP_QUERY = "http://api.brain-map.org/api/v2/data/query.json"
_MODEL = "model::ApiCellTypesSpecimenDetail"


@register_tool("AllenCellTypesSpecimensTool")
class AllenCellTypesSpecimensTool(BaseTool):
    """Search Allen Cell Types single-neuron specimens (ephys/morphology)."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        criteria = _MODEL
        filters: List[str] = []
        species = (arguments.get("species") or "").strip()
        if species:
            filters.append(f"donor__species$eq'{species}'")
        structure = (arguments.get("structure") or "").strip()
        if structure:
            filters.append(f"structure__name$il'%{structure}%'")
        if filters:
            criteria += ",rma::criteria," + ",".join(f"[{f}]" for f in filters)
        try:
            num_rows = max(1, min(int(arguments.get("limit") or 20), 100))
        except (TypeError, ValueError):
            num_rows = 20

        params = {"criteria": criteria, "num_rows": num_rows}
        try:
            resp = requests.get(
                BRAINMAP_QUERY,
                params=params,
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            payload = resp.json()
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Allen Brain-Map request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Allen Brain-Map request failed: {e}"}
        except ValueError:
            return {
                "status": "error",
                "error": "Allen Brain-Map returned a non-JSON response",
            }

        if not payload.get("success", False):
            return {
                "status": "error",
                "error": f"Allen Brain-Map query error: {payload.get('msg')}",
            }
        rows = payload.get("msg", []) or []
        return {
            "status": "success",
            "data": [self._summarize(r) for r in rows if isinstance(r, dict)],
            "metadata": {
                "total_available": payload.get("total_rows"),
                "returned": len(rows),
                "query": {"species": species or None, "structure": structure or None},
                "source": "Allen Cell Types Database",
            },
        }

    @staticmethod
    def _summarize(r: Dict[str, Any]) -> Dict[str, Any]:
        def clean(v: Any) -> Optional[str]:
            return v.strip('"') if isinstance(v, str) else v

        return {
            "specimen_name": clean(r.get("name")),
            "species": clean(r.get("donor__species")),
            "sex": clean(r.get("donor__sex")),
            "age": clean(r.get("donor__age")),
            "disease_state": clean(r.get("donor__disease_state")),
            "brain_structure": clean(r.get("structure__name")),
            "transgenic_line": clean(r.get("line_name")) or None,
            "avg_firing_rate": r.get("ef__avg_firing_rate"),
            "input_resistance": r.get("ef__ri"),
            "tau": r.get("ef__tau"),
            "upstroke_downstroke_ratio": r.get(
                "ef__upstroke_downstroke_ratio_long_square"
            ),
            "has_reconstruction": r.get("nr__reconstruction_type") not in (None, ""),
        }
