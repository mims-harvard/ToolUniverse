"""
RGD Strain Tool - Rat Genome Database (RGD) rat strain catalog + strain models.

Rat inbred/congenic/transgenic STRAINS are RGD's flagship rat-specific resource and
are not exposed by the Alliance of Genome Resources, MGI, or the existing gene-centric
RGD tools. This tool covers the strain catalog (search + symbol lookup) and the curated
disease / phenotype / variant ontology annotations that turn a strain into a documented
rat disease MODEL (e.g. SHR -> Left Ventricular Hypertrophy, arterial blood pressure
trait).

API: https://rest.rgd.mcw.edu/rgdws/
No authentication required.

Confirmed-live endpoints used (2026-06):
  GET /strains/all                      -> bulk catalog of every rat strain (~4600)
  GET /annotations/rgdId/{rgdId}        -> ontology annotations for a strain RGD ID

The strain catalog is a single 5.9 MB bulk dump; it is fetched once and cached at the
class level so repeated calls (e.g. symbol lookups) do not re-download it.
"""

import requests
from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool


RGD_BASE = "https://rest.rgd.mcw.edu/rgdws"

# RGD ontology aspect codes -> human-readable category
_ASPECT_LABELS = {
    "D": "disease",
    "V": "phenotype",  # clinical/measurement & mammalian-phenotype variants
    "N": "phenotype",
    "S": "strain",
    "P": "biological_process",
    "F": "molecular_function",
    "C": "cellular_component",
    "W": "pathway",
    "E": "experimental_condition",
}


@register_tool("RGDStrainTool")
class RGDStrainTool(BaseTool):
    """
    Tool for querying Rat Genome Database (RGD) rat strains.

    Supported operations (dispatched by fields.operation):
    - search_strains: keyword/type filter across the strain catalog
    - get_strain: exact strain-symbol lookup -> full strain record
    - get_strain_annotations: disease/phenotype/variant annotations for a strain
    """

    # Class-level cache of the bulk strain catalog (shared across instances/calls).
    _STRAIN_RECORDS: Optional[List[Dict[str, Any]]] = None

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = 30
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_strains"
        )
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "ToolUniverse/1.0 (https://github.com/mims-harvard/ToolUniverse)"
            }
        )

    # ------------------------------------------------------------------ #
    # Dispatch
    # ------------------------------------------------------------------ #
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            handlers = {
                "search_strains": self._search_strains,
                "get_strain": self._get_strain,
                "get_strain_annotations": self._get_strain_annotations,
            }
            handler = handlers.get(self.operation)
            if handler is None:
                return {
                    "status": "error",
                    "error": f"Unknown operation: {self.operation}",
                }
            return handler(arguments or {})
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "RGD API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to RGD API"}
        except Exception as e:  # never raise out of a tool
            return {"status": "error", "error": f"RGD API error: {str(e)}"}

    # ------------------------------------------------------------------ #
    # Catalog loading (cached)
    # ------------------------------------------------------------------ #
    def _load_catalog(self) -> List[Dict[str, Any]]:
        if RGDStrainTool._STRAIN_RECORDS is not None:
            return RGDStrainTool._STRAIN_RECORDS
        resp = self.session.get(f"{RGD_BASE}/strains/all", timeout=self.timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"RGD /strains/all returned HTTP {resp.status_code}")
        data = resp.json()
        if not isinstance(data, list):
            data = []
        RGDStrainTool._STRAIN_RECORDS = data
        return data

    @staticmethod
    def _slim_strain(rec: Dict[str, Any]) -> Dict[str, Any]:
        """Project a raw strain record onto the documented schema fields."""
        return {
            "rgd_id": rec.get("rgdId"),
            "symbol": rec.get("symbol"),
            "name": rec.get("name"),
            "full_strain_name": rec.get("strain"),
            "substrain": rec.get("substrain"),
            "strain_type": rec.get("strainTypeName"),
            "genetics": rec.get("genetics"),
            "origin": rec.get("origin"),
            "source": rec.get("source"),
            "background_strain_rgd_id": rec.get("backgroundStrainRgdId"),
            "research_use": rec.get("researchUse"),
            "description": rec.get("description"),
        }

    # ------------------------------------------------------------------ #
    # Operations
    # ------------------------------------------------------------------ #
    def _search_strains(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = (arguments.get("query") or "").strip().lower()
        strain_type = (arguments.get("strain_type") or "").strip().lower()
        limit = arguments.get("limit", 25)
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 25
        limit = max(1, min(limit, 200))

        if not query and not strain_type:
            return {
                "status": "error",
                "error": "Provide at least one of 'query' (keyword) or 'strain_type'.",
            }

        catalog = self._load_catalog()
        matches = []
        for rec in catalog:
            if strain_type and (rec.get("strainTypeName") or "").lower() != strain_type:
                continue
            if query:
                haystack = " ".join(
                    str(rec.get(f) or "")
                    for f in ("symbol", "name", "strain", "genetics", "description")
                ).lower()
                if query not in haystack:
                    continue
            matches.append(self._slim_strain(rec))

        return {
            "status": "success",
            "data": matches[:limit],
            "metadata": {
                "query": arguments.get("query"),
                "strain_type": arguments.get("strain_type"),
                "total_matches": len(matches),
                "returned": min(len(matches), limit),
                "source": "RGD /strains/all",
            },
        }

    def _resolve_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        symbol_l = symbol.strip().lower()
        for rec in self._load_catalog():
            if (rec.get("symbol") or "").lower() == symbol_l:
                return rec
        return None

    def _require_strain(self, arguments: Dict[str, Any]):
        """Validate the 'symbol' argument and resolve it to a strain record.

        Returns ``(rec, None)`` on success or ``(None, error_dict)`` so callers
        can short-circuit with the error response.
        """
        symbol = (arguments.get("symbol") or "").strip()
        if not symbol:
            return None, {
                "status": "error",
                "error": "Parameter 'symbol' is required (e.g. 'SHR', 'BN').",
            }
        rec = self._resolve_symbol(symbol)
        if rec is None:
            return None, {
                "status": "error",
                "error": f"No RGD rat strain found with symbol '{symbol}'.",
            }
        return rec, None

    def _get_strain(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        rec, error = self._require_strain(arguments)
        if error is not None:
            return error
        return {
            "status": "success",
            "data": self._slim_strain(rec),
            "metadata": {"source": "RGD /strains/all"},
        }

    def _get_strain_annotations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        rec, error = self._require_strain(arguments)
        if error is not None:
            return error
        rgd_id = rec.get("rgdId")

        category = (arguments.get("category") or "").strip().lower()

        resp = self.session.get(
            f"{RGD_BASE}/annotations/rgdId/{rgd_id}", timeout=self.timeout
        )
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": (
                    f"RGD /annotations/rgdId/{rgd_id} returned HTTP {resp.status_code}"
                ),
            }
        raw = resp.json()
        if not isinstance(raw, list):
            raw = []

        annotations = []
        for a in raw:
            aspect = a.get("aspect")
            cat = _ASPECT_LABELS.get(aspect, "other")
            if category and cat != category:
                continue
            annotations.append(
                {
                    "term": a.get("term"),
                    "term_acc": a.get("termAcc"),
                    "category": cat,
                    "aspect": aspect,
                    "qualifier": a.get("qualifier"),
                    "evidence": a.get("evidence"),
                    "data_source": a.get("dataSrc"),
                    "ref_rgd_id": a.get("refRgdId"),
                }
            )

        return {
            "status": "success",
            "data": annotations,
            "metadata": {
                "symbol": rec.get("symbol"),
                "strain_rgd_id": rgd_id,
                "category_filter": arguments.get("category"),
                "total": len(annotations),
                "source": f"RGD /annotations/rgdId/{rgd_id}",
            },
        }
