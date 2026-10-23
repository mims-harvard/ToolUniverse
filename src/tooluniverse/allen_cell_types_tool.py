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

BRAINMAP_QUERY = "https://api.brain-map.org/api/v2/data/query.json"
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
        species_value = arguments.get("species")
        if species_value is not None and not isinstance(species_value, str):
            return {
                "status": "error",
                "error": "species must be a string when provided",
                "parameter": "species",
            }
        species = (species_value or "").strip()
        if species:
            filters.append(f"donor__species$eq'{species}'")
        structure_value = arguments.get("structure")
        if structure_value is not None and not isinstance(structure_value, str):
            return {
                "status": "error",
                "error": "structure must be a string when provided",
                "parameter": "structure",
            }
        structure = (structure_value or "").strip()
        if structure:
            filters.append(f"structure__name$il'%{structure}%'")
        if filters:
            criteria += ",rma::criteria," + ",".join(f"[{f}]" for f in filters)
        num_rows = arguments.get("limit", 20)
        if (
            isinstance(num_rows, bool)
            or not isinstance(num_rows, int)
            or not 1 <= num_rows <= 2000
        ):
            return {
                "status": "error",
                "error": "limit must be an integer between 1 and 2000",
                "parameter": "limit",
            }
        start_row = arguments.get("start_row", 0)
        if (
            isinstance(start_row, bool)
            or not isinstance(start_row, int)
            or start_row < 0
        ):
            return {
                "status": "error",
                "error": "start_row must be a non-negative integer",
                "parameter": "start_row",
            }

        params = {
            "criteria": criteria,
            "num_rows": num_rows,
            "start_row": start_row,
        }
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
        if not isinstance(rows, list):
            return {
                "status": "error",
                "error": "Allen Brain-Map returned an unexpected result payload",
            }
        total = payload.get("total_rows")
        if isinstance(total, bool) or not isinstance(total, int) or total < 0:
            total = len(rows)
        page_advance = len(rows)
        has_more = page_advance > 0 and start_row + page_advance < total
        truncated = start_row > 0 or has_more
        specimens = [self._summarize(r) for r in rows if isinstance(r, dict)]
        return {
            "status": "success",
            "data": specimens,
            "metadata": {
                "total_available": total,
                "returned": len(specimens),
                "limit": num_rows,
                "start_row": start_row,
                "has_more": has_more,
                "next_start_row": (start_row + page_advance if has_more else None),
                "truncated": truncated,
                "result_set_complete": not truncated,
                "query": {"species": species or None, "structure": structure or None},
                "source": "Allen Cell Types Database",
            },
        }

    @staticmethod
    def _summarize(r: Dict[str, Any]) -> Dict[str, Any]:
        def clean(v: Any) -> Optional[str]:
            return v.strip('"') if isinstance(v, str) else v

        return {
            "specimen_id": r.get("specimen__id"),
            "specimen_name": clean(r.get("specimen__name") or r.get("name")),
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
