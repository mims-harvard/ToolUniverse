# hubmap_sample_tool.py
"""
HuBMAP Sample/Donor spatial-context tool for ToolUniverse.

Complements the existing HuBMAPTool (dataset-level search) by exposing the
*biospecimen* layer of the Human BioMolecular Atlas Program: the physical
tissue Samples (anatomical blocks, sections, organs, suspensions) and the
human Donors they come from.

The standout content here is RUI (Registration User Interface) spatial
registration: tissue blocks/sections registered into the HuBMAP Common
Coordinate Framework (CCF) carry a `rui_location` JSON object with the
3-D dimensions, placement target reference organ, and CCF/UBERON
`ccf_annotations` describing exactly which anatomical structures the
specimen overlaps. None of the dataset-level tools surface this, nor the
UMLS-coded donor demographics (age / sex / race / BMI).

APIs (no authentication required for public entities):
- Search API: https://search.api.hubmapconsortium.org/v3/search  (Elasticsearch)

Operations:
- search_samples : find tissue Samples by organ code + sample_category, with
                   RUI spatial-registration flag.
- get_sample     : full Sample record including parsed rui_location (CCF
                   placement, dimensions, UBERON annotations) and donor link.
- search_donors  : find human Donors, with normalized demographics
                   (age / sex / race / BMI from metadata.organ_donor_data).
"""

import json
import requests
from typing import Any

from .base_tool import BaseTool
from .tool_registry import register_tool


HUBMAP_SEARCH_URL = "https://search.api.hubmapconsortium.org/v3/search"

# 2-letter RUI organ codes used by HuBMAP origin_samples.organ
ORGAN_CODE_NAMES = {
    "LK": "Left Kidney",
    "RK": "Right Kidney",
    "LI": "Large Intestine",
    "SI": "Small Intestine",
    "HT": "Heart",
    "LV": "Liver",
    "LL": "Left Lung",
    "RL": "Right Lung",
    "LU": "Lung",
    "SP": "Spleen",
    "TH": "Thymus",
    "LY": "Lymph Node",
    "LN": "Lymph Node",
    "BL": "Bladder",
    "PA": "Pancreas",
    "SK": "Skin",
    "BR": "Brain",
    "BM": "Bone Marrow",
    "MU": "Muscle",
    "UT": "Uterus",
    "PL": "Placenta",
    "LE": "Left Eye",
    "RE": "Right Eye",
    "RF": "Right Fallopian Tube",
    "LF": "Left Fallopian Tube",
    "LO": "Left Ovary",
    "RO": "Right Ovary",
    "BD": "Blood",
    "BV": "Blood Vasculature",
    "RB": "Right Bronchus",
    "LB": "Left Bronchus",
    "RN": "Right Kidney (RN)",
}


@register_tool("HuBMAPSampleTool")
class HuBMAPSampleTool(BaseTool):
    """
    Query the HuBMAP biospecimen layer: tissue Samples (with CCF/RUI spatial
    registration) and human Donors (with UMLS-coded demographics).

    Dispatched by the `operation` field. No authentication required.
    """

    def __init__(self, tool_config: dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.operation = fields.get("operation", "search_samples")

    # ------------------------------------------------------------------ #
    # dispatch
    # ------------------------------------------------------------------ #
    def run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            if self.operation == "search_samples":
                return self._search_samples(arguments)
            elif self.operation == "get_sample":
                return self._get_sample(arguments)
            elif self.operation == "search_donors":
                return self._search_donors(arguments)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown operation: {self.operation}",
                }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"HuBMAP API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to HuBMAP API"}
        except Exception as e:  # never raise
            return {"status": "error", "error": str(e)}

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        resp = requests.post(
            HUBMAP_SEARCH_URL,
            json=body,
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _first_organ_code(src: dict[str, Any]) -> str | None:
        """Return the first mapped organ code from origin_samples, or None."""
        for s in src.get("origin_samples", []):
            if s.get("organ"):
                return s["organ"]
        return None

    @staticmethod
    def _parse_rui(rui_raw: Any) -> dict[str, Any] | None:
        """Parse the rui_location JSON (stored as a string) into a compact dict."""
        if not rui_raw:
            return None
        rui = rui_raw
        if isinstance(rui_raw, str):
            try:
                rui = json.loads(rui_raw)
            except (ValueError, TypeError):
                return None
        if not isinstance(rui, dict):
            return None
        placement = rui.get("placement") or {}
        return {
            "registered": True,
            "placement_target": placement.get("target"),
            "x_dimension": rui.get("x_dimension"),
            "y_dimension": rui.get("y_dimension"),
            "z_dimension": rui.get("z_dimension"),
            "dimension_units": rui.get("dimension_units"),
            "ccf_annotations": rui.get("ccf_annotations") or [],
        }

    @staticmethod
    def _donor_demographics(src: dict[str, Any]) -> dict[str, Any]:
        """Normalize metadata.organ_donor_data UMLS rows into age/sex/race/bmi/etc."""
        demo: dict[str, Any] = {}
        rows = (src.get("metadata") or {}).get("organ_donor_data") or []
        for row in rows:
            if not isinstance(row, dict):
                continue
            label = (
                row.get("grouping_concept_preferred_term")
                or row.get("preferred_term")
                or ""
            )
            value = row.get("data_value")
            units = row.get("units")
            if not label:
                continue
            key = label.strip().lower().replace(" ", "_")
            if units and row.get("data_type") == "Numeric":
                demo[key] = f"{value} {units}".strip()
            else:
                demo[key] = value
        return demo

    # ------------------------------------------------------------------ #
    # operations
    # ------------------------------------------------------------------ #
    def _search_samples(self, arguments: dict[str, Any]) -> dict[str, Any]:
        organ = arguments.get("organ")
        sample_category = arguments.get("sample_category")
        registered_only = arguments.get("registered_only", False)
        limit = min(int(arguments.get("limit", 10) or 10), 50)

        must: list[dict[str, Any]] = [{"match": {"entity_type": "Sample"}}]
        if organ:
            must.append({"match": {"origin_samples.organ": str(organ).upper()}})
        if sample_category:
            must.append({"match": {"sample_category": str(sample_category).lower()}})
        if registered_only:
            must.append({"exists": {"field": "rui_location"}})

        body = {
            "size": limit,
            "query": {"bool": {"must": must}},
            "_source": [
                "hubmap_id",
                "uuid",
                "entity_type",
                "sample_category",
                "origin_samples",
                "group_name",
                "rui_location",
                "donor",
                "created_timestamp",
            ],
        }
        data = self._post(body)
        hits = data.get("hits", {}).get("hits", [])
        total = data.get("hits", {}).get("total", {}).get("value", 0)

        samples = []
        for h in hits:
            src = h.get("_source", {})
            code = self._first_organ_code(src)
            donor = src.get("donor") or {}
            samples.append(
                {
                    "hubmap_id": src.get("hubmap_id"),
                    "uuid": src.get("uuid"),
                    "sample_category": src.get("sample_category"),
                    "organ_code": code,
                    "organ_name": ORGAN_CODE_NAMES.get(code) if code else None,
                    "group_name": src.get("group_name"),
                    "spatially_registered": bool(src.get("rui_location")),
                    "donor_hubmap_id": donor.get("hubmap_id"),
                }
            )

        return {
            "status": "success",
            "data": {
                "total": total,
                "returned": len(samples),
                "samples": samples,
            },
        }

    def _get_sample(self, arguments: dict[str, Any]) -> dict[str, Any]:
        hubmap_id = arguments.get("hubmap_id")
        if not hubmap_id:
            return {"status": "error", "error": "hubmap_id is required"}

        body = {
            "size": 1,
            "query": {
                "bool": {
                    "must": [
                        {"match": {"entity_type": "Sample"}},
                        {"term": {"hubmap_id.keyword": hubmap_id}},
                    ]
                }
            },
        }
        data = self._post(body)
        hits = data.get("hits", {}).get("hits", [])
        if not hits:
            return {
                "status": "error",
                "error": f"No HuBMAP Sample found for id '{hubmap_id}'",
            }

        src = hits[0].get("_source", {})
        code = self._first_organ_code(src)
        donor = src.get("donor") or {}

        return {
            "status": "success",
            "data": {
                "hubmap_id": src.get("hubmap_id"),
                "uuid": src.get("uuid"),
                "entity_type": src.get("entity_type"),
                "sample_category": src.get("sample_category"),
                "organ_code": code,
                "organ_name": ORGAN_CODE_NAMES.get(code) if code else None,
                "group_name": src.get("group_name"),
                "data_access_level": src.get("data_access_level"),
                "protocol_url": src.get("protocol_url"),
                "donor_hubmap_id": donor.get("hubmap_id"),
                "rui_location": self._parse_rui(src.get("rui_location")),
                "created_timestamp": src.get("created_timestamp"),
            },
        }

    def _search_donors(self, arguments: dict[str, Any]) -> dict[str, Any]:
        group_name = arguments.get("group_name")
        query_text = arguments.get("query")
        limit = min(int(arguments.get("limit", 10) or 10), 50)

        must: list[dict[str, Any]] = [{"match": {"entity_type": "Donor"}}]
        if group_name:
            must.append({"match": {"group_name": group_name}})
        if query_text:
            must.append(
                {
                    "multi_match": {
                        "query": query_text,
                        "fields": [
                            "description",
                            "group_name",
                            "metadata.organ_donor_data.data_value",
                            "metadata.organ_donor_data.preferred_term",
                        ],
                    }
                }
            )

        body = {
            "size": limit,
            "query": {"bool": {"must": must}},
            "_source": [
                "hubmap_id",
                "uuid",
                "entity_type",
                "group_name",
                "metadata",
                "created_timestamp",
            ],
        }
        data = self._post(body)
        hits = data.get("hits", {}).get("hits", [])
        total = data.get("hits", {}).get("total", {}).get("value", 0)

        donors = []
        for h in hits:
            src = h.get("_source", {})
            donors.append(
                {
                    "hubmap_id": src.get("hubmap_id"),
                    "uuid": src.get("uuid"),
                    "group_name": src.get("group_name"),
                    "demographics": self._donor_demographics(src),
                }
            )

        return {
            "status": "success",
            "data": {
                "total": total,
                "returned": len(donors),
                "donors": donors,
            },
        }
