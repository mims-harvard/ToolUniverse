# fda_label_tool.py
"""
FDA Drug Label tool for ToolUniverse.

Queries the openFDA drug label API to retrieve official FDA-approved
prescribing information including indications, dosing, contraindications,
warnings, drug interactions, and pharmacology.

API: https://open.fda.gov/apis/drug/label/
No authentication required. Optional API key raises rate limits.
"""

import requests
from typing import Any

from .base_tool import BaseTool
from .tool_registry import register_tool

FDA_LABEL_URL = "https://api.fda.gov/drug/label.json"


def _extract_label(result: dict) -> dict:
    """Extract key clinical sections from a raw openFDA label record."""
    openfda = result.get("openfda", {})
    brand = openfda.get("brand_name", [])
    generic = openfda.get("generic_name", [])
    mfr = openfda.get("manufacturer_name", [])
    route = openfda.get("route", [])
    pharm = openfda.get("pharm_class_epc", [])
    rxcui = openfda.get("rxcui", [])

    def first(lst, sep=" / "):
        return sep.join(lst[:2]) if lst else None

    def section(key):
        val = result.get(key, [])
        return " ".join(val)[:2000] if val else None

    return {
        "brand_name": first(brand),
        "generic_name": first(generic),
        "manufacturer": first(mfr),
        "route": first(route),
        "pharm_class": first(pharm),
        "rxcui": rxcui[:5] if rxcui else None,
        "boxed_warning": section("boxed_warning"),
        "indications_and_usage": section("indications_and_usage"),
        "dosage_and_administration": section("dosage_and_administration"),
        "dosage_forms_and_strengths": section("dosage_forms_and_strengths"),
        "contraindications": section("contraindications"),
        "warnings_and_precautions": section("warnings_and_precautions")
        or section("warnings_and_cautions"),
        "adverse_reactions": section("adverse_reactions"),
        "drug_interactions": section("drug_interactions"),
        "use_in_specific_populations": section("use_in_specific_populations"),
        "clinical_pharmacology": section("clinical_pharmacology"),
        "mechanism_of_action": section("mechanism_of_action"),
        "spl_id": result.get("id"),
    }


@register_tool("FDALabelTool")
class FDALabelTool(BaseTool):
    """
    Tool for querying FDA-approved drug label (prescribing information).

    Supports searching by drug name, indication, or listing drug classes.
    Returns official FDA clinical content: indications, dosing,
    contraindications, warnings, drug interactions, and adverse reactions.
    """

    def __init__(self, tool_config: dict[str, Any]):
        super().__init__(tool_config)
        self.query_type = tool_config.get("fields", {}).get("query_type", "search")

    def run(self, arguments: dict[str, Any]) -> Any:
        try:
            qt = self.query_type
            if qt == "search":
                return self._search(arguments)
            elif qt == "get":
                return self._get_label(arguments)
            elif qt == "list_classes":
                return self._list_classes(arguments)
            return {"error": f"Unknown query_type: {qt}"}
        except requests.exceptions.Timeout:
            return {"error": "openFDA request timed out"}
        except requests.exceptions.RequestException as e:
            return {"error": f"openFDA request failed: {e}"}
        except Exception as e:
            return {"error": f"Unexpected error: {e}"}

    def _search(self, arguments: dict) -> Any:
        drug_name = arguments.get("drug_name")
        indication = arguments.get("indication")
        limit = min(int(arguments.get("limit", 5)), 20)

        if not drug_name and not indication:
            return {"error": "Provide drug_name or indication"}

        if drug_name:
            # Search both generic and brand names
            q = f'openfda.generic_name:"{drug_name}"+openfda.brand_name:"{drug_name}"'
        else:
            q = f'indications_and_usage:"{indication}"'

        resp = requests.get(
            FDA_LABEL_URL,
            params={"search": q, "limit": limit},
            timeout=20,
        )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        return [_extract_label(r) for r in results]

    def _get_label(self, arguments: dict) -> Any:
        drug_name = arguments.get("drug_name", "")
        if not drug_name:
            return {"error": "drug_name is required"}

        q = f'openfda.generic_name:"{drug_name}"+openfda.brand_name:"{drug_name}"'
        resp = requests.get(
            FDA_LABEL_URL,
            params={"search": q, "limit": 1},
            timeout=20,
        )
        if resp.status_code == 404:
            return {"error": f"No FDA label found for '{drug_name}'"}
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if not results:
            return {"error": f"No FDA label found for '{drug_name}'"}
        return _extract_label(results[0])

    def _list_classes(self, arguments: dict) -> Any:
        limit = min(int(arguments.get("limit", 20)), 100)
        resp = requests.get(
            FDA_LABEL_URL,
            params={
                "count": "openfda.pharm_class_epc.exact",
                "limit": limit,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        return [{"drug_class": r["term"], "count": r["count"]} for r in results]
