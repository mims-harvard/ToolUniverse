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
            # Which brain each neuron came from. The tool promised donor
            # metadata and returned only the donor's attributes, so two
            # specimens from one donor could not be told from two donors.
            "donor_id": r.get("donor__id"),
            "donor_name": clean(r.get("donor__name")),
            "donor_race": clean(r.get("donor__race")),
            "years_of_seizure_history": r.get("donor__years_of_seizure_history"),
            "brain_structure": clean(r.get("structure__name")),
            # Layer 3 and layer 5 pyramidal neurons are different cell
            # types. A cell-types specimen search returned the structure
            # and not the layer within it.
            "cortical_layer": clean(r.get("structure__layer")),
            "structure_acronym": clean(r.get("structure__acronym")),
            "structure_id": r.get("structure__id"),
            "hemisphere": clean(r.get("specimen__hemisphere")),
            # Soma position in the common coordinate framework. Measured
            # per cell for mouse (60 distinct positions in 60 sampled
            # specimens); for human it is coarser, 12 distinct positions
            # across 60 specimens from 9 donors, so treat it as the block
            # the cell came from rather than the cell's own coordinate.
            "soma_location": (
                {
                    "x": r.get("csl__x"),
                    "y": r.get("csl__y"),
                    "z": r.get("csl__z"),
                    "normalized": r.get("csl__normalized"),
                }
                if r.get("csl__x") is not None
                else None
            ),
            "transgenic_line": clean(r.get("line_name")) or None,
            "avg_firing_rate": r.get("ef__avg_firing_rate"),
            "input_resistance": r.get("ef__ri"),
            "tau": r.get("ef__tau"),
            "upstroke_downstroke_ratio": r.get(
                "ef__upstroke_downstroke_ratio_long_square"
            ),
            # The description promises electrophysiology. Resting membrane
            # potential and rheobase are the two most basic intrinsic
            # properties a neuron has, and neither reached the caller.
            "resting_potential_mv": r.get("ef__vrest"),
            "rheobase_pa": r.get("ef__threshold_i_long_square"),
            "adaptation_index": r.get("ef__adaptation"),
            "f_i_curve_slope": r.get("ef__f_i_curve_slope"),
            "avg_interspike_interval_ms": r.get("ef__avg_isi"),
            "fast_trough_mv": r.get("ef__fast_trough_v_long_square"),
            "ramp_peak_time_s": r.get("ef__peak_t_ramp"),
            # Spiny or aspiny is the standard morphological proxy for
            # excitatory versus inhibitory, and whether the apical dendrite
            # is intact says whether the reconstruction can be trusted.
            "dendrite_type": clean(r.get("tag__dendrite_type")),
            "apical_dendrite": clean(r.get("tag__apical")),
            "reconstruction_type": clean(r.get("nr__reconstruction_type")) or None,
            "has_reconstruction": r.get("nr__reconstruction_type") not in (None, ""),
            # How many models the Allen Institute fit to this cell.
            "model_counts": {
                "glif": r.get("m__glif"),
                "biophysical_perisomatic": r.get("m__biophys_perisomatic"),
                "biophysical_all_active": r.get("m__biophys_all_active"),
            },
        }
