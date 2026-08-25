# membrane_topology_tool.py
"""
Structure-derived membrane protein topology tools for ToolUniverse.

Two complementary resources for how a membrane protein sits in the bilayer:

  OPM    Orientations of Proteins in Membranes. Positions solved structures
         in the membrane and reports hydrophobic thickness, tilt angle, and
         the calculated transfer free energy.
  TopDB  Topology Data Bank of Transmembrane Proteins. Curated per-segment
         topology with the experimental evidence behind each assignment.

ToolUniverse can already *predict* topology from sequence
(EBI_predict_membrane_topology, which runs Phobius). These tools supply the
structure-derived and experimentally curated counterpart, so a prediction can
be checked against what is actually known for a solved structure.

APIs: https://opm-back.cc.lehigh.edu/opm-backend
      https://topdb.unitmp.org/api/v1
No authentication required.
"""

from typing import Dict, Any, List

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

OPM_BASE_URL = "https://opm-back.cc.lehigh.edu/opm-backend"
TOPDB_BASE_URL = "https://topdb.unitmp.org/api/v1"


def _as_list(value: Any) -> List[Any]:
    """TopDB collapses single-element arrays to a bare object."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _float(value: Any) -> Any:
    """Parse a numeric attribute TopDB returns as a string."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> Any:
    """Parse an integer attribute, returning None when malformed."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _attrs(node: Any) -> Dict[str, Any]:
    """Read the @attributes block TopDB uses for element attributes."""
    if isinstance(node, dict):
        attrs = node.get("@attributes")
        if isinstance(attrs, dict):
            return attrs
    return {}


@register_tool("OPMTool")
class OPMTool(BaseTool):
    """
    Tool for querying Orientations of Proteins in Membranes.

    Returns membrane placement for solved structures: hydrophobic thickness,
    tilt angle, transfer free energy, and the membrane and family the protein
    is assigned to.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_structures"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the OPM query."""
        try:
            if self.operation == "search_structures":
                return self._search(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"OPM request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to OPM. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"OPM returned HTTP {code}"}
        except ValueError:
            return {"status": "error", "error": "OPM returned a non-JSON response"}
        except Exception as e:
            return {"status": "error", "error": f"Error querying OPM: {str(e)}"}

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search OPM by protein name or PDB identifier."""
        query = (arguments.get("query") or "").strip()
        if not query:
            return {
                "status": "error",
                "error": "query is required: a protein name such as 'rhodopsin' "
                "or a PDB identifier such as '1uaz'.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 25
        limit = min(limit, 100)

        response = requests.get(
            f"{OPM_BASE_URL}/primary_structures",
            params={"search": query, "pageSize": limit, "pageNum": 1},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()

        objects = payload.get("objects") or []
        rows = [
            {
                "pdb_id": o.get("pdbid"),
                "name": o.get("name"),
                "family": o.get("family_name_cache"),
                "membrane": o.get("membrane_name_cache"),
                "hydrophobic_thickness_angstrom": o.get("thickness"),
                "thickness_error": o.get("thicknesserror"),
                "tilt_angle_degrees": o.get("tilt"),
                "transfer_energy_kcal_per_mol": o.get("gibbs"),
                "resolution_angstrom": o.get("resolution"),
                "description": o.get("description"),
            }
            for o in objects
            if isinstance(o, dict)
        ]

        if not rows:
            return {
                "status": "error",
                "error": f"No OPM structures matching '{query}'. OPM only "
                "contains proteins with solved structures positioned in a "
                "membrane.",
            }

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "query": query,
                "total_matching": payload.get("total_objects"),
                "returned": len(rows),
                "note": "Transfer energy is negative for favourable membrane "
                "insertion; thickness is the hydrophobic bilayer span.",
                "source": "OPM (Orientations of Proteins in Membranes)",
            },
        }


@register_tool("TopDBTool")
class TopDBTool(BaseTool):
    """
    Tool for retrieving curated transmembrane topology from TopDB.

    Returns per-segment topology for a protein, with the type of each segment
    and the experimental evidence supporting the assignment.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.operation = tool_config.get("fields", {}).get("operation", "get_topology")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the TopDB query."""
        try:
            if self.operation == "get_topology":
                return self._get_topology(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"TopDB request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to TopDB. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"TopDB returned HTTP {code}"}
        except ValueError:
            return {"status": "error", "error": "TopDB returned a non-JSON response"}
        except Exception as e:
            return {"status": "error", "error": f"Error querying TopDB: {str(e)}"}

    def _get_topology(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch curated topology for a UniProt accession or TopDB identifier."""
        identifier = (arguments.get("identifier") or "").strip()
        if not identifier:
            return {
                "status": "error",
                "error": "identifier is required: a UniProt accession such as "
                "'P02699' or a TopDB entry name such as 'OPSD_BOVIN'.",
            }

        response = requests.get(
            f"{TOPDB_BASE_URL}/entry/{identifier}.json", timeout=self.timeout
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No TopDB entry for '{identifier}'. TopDB covers "
                "transmembrane proteins with experimental topology evidence.",
            }
        response.raise_for_status()
        entry = response.json()
        if not isinstance(entry, dict) or not entry.get("Topology"):
            return {
                "status": "error",
                "error": f"TopDB returned no topology for '{identifier}'.",
            }

        top_attrs = _attrs(entry)
        topology = entry.get("Topology") or {}

        regions: List[Dict[str, Any]] = []
        for region in _as_list((topology.get("Regions") or {}).get("Region")):
            attrs = _attrs(region)
            if not attrs:
                continue
            regions.append(
                {
                    "location": attrs.get("Loc"),
                    "start": _int(attrs.get("Begin")),
                    "end": _int(attrs.get("End")),
                }
            )

        # Experimental evidence, one record per studied region.
        evidence: List[Dict[str, Any]] = []
        for region in _as_list((entry.get("Experiments") or {}).get("Region")):
            attrs = _attrs(region)
            exp = region.get("Exp") if isinstance(region, dict) else None
            exp = exp[0] if isinstance(exp, list) and exp else exp
            evidence.append(
                {
                    "location": attrs.get("Loc"),
                    "start": _int(attrs.get("Begin")),
                    "end": _int(attrs.get("End")),
                    "experiment_type": (exp or {}).get("Type"),
                    "experiment_subtype": (exp or {}).get("Subtype"),
                }
            )

        declared_tm = _int(_attrs(topology.get("Numtm")).get("Count"))
        counted_tm = sum(
            1 for r in regions if (r["location"] or "").lower() == "membrane"
        )

        return {
            "status": "success",
            "data": {
                "topdb_id": top_attrs.get("ID"),
                "name": entry.get("Name"),
                "protein_type": top_attrs.get("type"),
                "transmembrane_region_count": declared_tm
                if declared_tm is not None
                else counted_tm,
                "reliability": _float(topology.get("Reliability")),
                "regions": regions,
                "experimental_evidence": evidence[:50],
                "evidence_count": len(evidence),
            },
            "metadata": {
                "identifier": identifier,
                "region_count": len(regions),
                "note": "Curated from experimental evidence; compare with the "
                "sequence-based prediction from EBI_predict_membrane_topology.",
                "source": "TopDB (UNITMP)",
            },
        }
