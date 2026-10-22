# fda_label_tool.py
"""
FDA Drug Label tool for ToolUniverse.

Queries the openFDA drug label API to retrieve official FDA-approved
prescribing information including indications, dosing, contraindications,
warnings, drug interactions, and pharmacology.

API: https://open.fda.gov/apis/drug/label/
No authentication required. Set the FDA_API_KEY env var to raise the
default ~40 req/min anonymous rate limit (https://open.fda.gov/apis/authentication/).
"""

import os
import requests
from typing import Any

from .base_tool import BaseTool
from .tool_registry import register_tool

FDA_LABEL_URL = "https://api.fda.gov/drug/label.json"

# Placeholder values users sometimes leave in FDA_API_KEY; treat as "unset".
_API_KEY_PLACEHOLDERS = {"none", "null", "your_fda_key_here", "your_key_here"}


def _valid_api_key(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    v = value.strip()
    return bool(v) and v.lower() not in _API_KEY_PLACEHOLDERS


def _ok(data: Any, **metadata: Any) -> dict:
    """Wrap a successful result in the standard ToolUniverse envelope.

    Error paths already return {status: error, ...}; this keeps the success
    path consistent with the project-wide {status, data, metadata} contract.
    """
    metadata.setdefault("source", "openFDA drug label")
    if isinstance(data, list):
        metadata.setdefault("count", len(data))
    return {"status": "success", "data": data, "metadata": metadata}


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
        self.api_key = os.getenv("FDA_API_KEY")

    def _params(self, **kwargs: Any) -> dict:
        """Build request params, adding api_key when a valid FDA_API_KEY is set.

        openFDA's anonymous tier is heavily rate-limited (~40 req/min); an
        API key raises that substantially. See https://open.fda.gov/apis/authentication/
        """
        if _valid_api_key(self.api_key):
            kwargs["api_key"] = self.api_key
        return kwargs

    def run(self, arguments: dict[str, Any]) -> Any:
        try:
            qt = self.query_type
            if qt == "search":
                return self._search(arguments)
            elif qt == "get":
                return self._get_label(arguments)
            elif qt == "list_classes":
                return self._list_classes(arguments)
            return {"status": "error", "error": f"Unknown query_type: {qt}"}
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "openFDA request timed out"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"openFDA request failed: {e}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {e}"}

    def _query_drug_fields(
        self, drug_name: str, limit: int, offset: int = 0
    ) -> dict | None:
        """Search generic_name then brand_name with quoted then unquoted fallback.

        Returns extracted label results on first match, or None if no results found.
        Quoted search finds exact matches; unquoted fallback catches salt forms
        (e.g., "tofacitinib" matching "TOFACITINIB CITRATE").
        """
        for field in ("openfda.generic_name", "openfda.brand_name"):
            for q in (f'{field}:"{drug_name}"', f"{field}:{drug_name}"):
                resp = requests.get(
                    FDA_LABEL_URL,
                    params=self._params(search=q, limit=limit, skip=offset),
                    timeout=20,
                )
                if resp.status_code == 404:
                    continue
                resp.raise_for_status()
                body = resp.json()
                results = body.get("results", [])
                if results:
                    return {
                        "labels": [_extract_label(r) for r in results],
                        "total": body.get("meta", {})
                        .get("results", {})
                        .get("total", len(results)),
                        "matched_query": q,
                    }
        return None

    def _search(self, arguments: dict) -> Any:
        drug_name = arguments.get("drug_name")
        indication = arguments.get("indication")
        limit = min(int(arguments.get("limit", 5)), 20)
        offset = max(0, int(arguments.get("offset", 0)))

        if not drug_name and not indication:
            return {"status": "error", "error": "Provide drug_name or indication"}

        if drug_name:
            match = self._query_drug_fields(drug_name, limit, offset)
            labels = match["labels"] if match else []
            total = match["total"] if match else 0
            next_offset = offset + len(labels)
            has_more = next_offset < total
            return _ok(
                labels,
                query=drug_name,
                query_field="drug_name",
                matched_query=match.get("matched_query") if match else None,
                total=total,
                returned=len(labels),
                offset=offset,
                has_more=has_more,
                next_offset=next_offset if has_more else None,
            )

        q = f'indications_and_usage:"{indication}"'
        resp = requests.get(
            FDA_LABEL_URL,
            params=self._params(search=q, limit=limit, skip=offset),
            timeout=20,
        )
        labels = []
        total = 0
        if resp.status_code != 404:
            resp.raise_for_status()
            body = resp.json()
            labels = [_extract_label(r) for r in body.get("results", [])]
            total = (
                body.get("meta", {}).get("results", {}).get("total", len(labels))
            )
        next_offset = offset + len(labels)
        has_more = next_offset < total
        return _ok(
            labels,
            query=indication,
            query_field="indication",
            total=total,
            returned=len(labels),
            offset=offset,
            has_more=has_more,
            next_offset=next_offset if has_more else None,
        )

    def _get_label(self, arguments: dict) -> Any:
        drug_name = arguments.get("drug_name", "")
        if not drug_name:
            return {"status": "error", "error": "drug_name is required"}

        match = self._query_drug_fields(drug_name, limit=10)
        if not match:
            return {"status": "error", "error": f"No FDA label found for '{drug_name}'"}
        results = match["labels"]

        dn_upper = drug_name.upper()

        def _match_score(r):
            brand = (r.get("brand_name") or "").upper()
            generic = (r.get("generic_name") or "").upper()
            if brand == dn_upper or generic == dn_upper:
                return 0
            return len(brand) or 999

        results.sort(key=_match_score)
        return _ok(results[0], query=drug_name)

    def _list_classes(self, arguments: dict) -> Any:
        limit = min(int(arguments.get("limit", 20)), 100)
        offset = max(0, int(arguments.get("offset", 0)))
        resp = requests.get(
            FDA_LABEL_URL,
            params=self._params(
                count="openfda.pharm_class_epc.exact",
                limit=1000,
            ),
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        page = results[offset : offset + limit]
        classes = [{"drug_class": r["term"], "count": r["count"]} for r in page]
        accessible_total = len(results)
        next_offset = offset + len(classes)
        has_more = next_offset < accessible_total
        return _ok(
            classes,
            accessible_total=accessible_total,
            total_is_exact=accessible_total < 1000,
            returned=len(classes),
            offset=offset,
            has_more=has_more,
            next_offset=next_offset if has_more else None,
        )
