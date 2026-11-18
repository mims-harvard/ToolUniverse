# health_canada_dpd_tool.py
"""
Health Canada Drug Product Database (DPD) tools for ToolUniverse.

The DPD lists every drug product that Health Canada has authorized for
sale: human, veterinary, radiopharmaceutical, biologic and disinfectant
products, marketed or cancelled. Each product has a Drug Identification
Number (DIN), active ingredients with strengths, dosage forms, routes,
schedules (prescription, OTC, narcotic) and an ATC code.

ToolUniverse covers the US market (openFDA, DailyMed, Orange Book,
Drugs@FDA) but had no Canadian regulatory source. These tools search the DPD
by brand name, DIN or active ingredient and read one product's full record.

API: https://health-products.canada.ca/api/drug/ (public, no key, JSON).
Two API habits the tools handle:

* ``drugproduct/?id=<unknown code>`` answers HTTP 200 with a record whose
  ``drug_code`` is 0 and every other field null, not a 404. The tools report
  that as "not found".
* The sub-resources (form, route, schedule, therapeuticclass) answer 404
  when a product has no entry; the tools report that as an empty list.

``activeingredient`` has no status filter: 1354 products hold acetaminophen,
and the 25 with the lowest drug codes are all cancelled (2026-11-18). For
``marketed_only`` the tool reads the list of marketed products once
(``drugproduct/?status=2``: about 13,400 rows, 3.4 MB) and keeps it for an hour.
"""

import threading
import time
from typing import Any, Dict, List, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

DPD_BASE_URL = "https://health-products.canada.ca/api/drug"
DEFAULT_LIMIT = 25
MAX_LIMIT = 100
INGREDIENT_DEFAULT_LIMIT = 10
INGREDIENT_MAX_LIMIT = 25  # each row costs one product lookup
MARKETED_STATUS = 2  # DPD status code for "Marketed"
MARKETED_TTL_S = 3600

# drug_code -> product record of every marketed product, read on first use.
_marketed: Dict[str, Any] = {"products": None, "fetched": 0.0}
_marketed_lock = threading.Lock()


class _DPDError(Exception):
    """A DPD answer that the tool reports as an error."""


class _NotFound(Exception):
    """A DPD endpoint answered 404 (no entry for this product)."""


def _product_row(p: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "drug_code": p.get("drug_code"),
        "din": p.get("drug_identification_number"),
        "brand_name": p.get("brand_name"),
        "descriptor": p.get("descriptor") or None,
        "class": p.get("class_name"),
        "company": p.get("company_name"),
        "number_of_active_ingredients": p.get("number_of_ais"),
        "ai_group_no": p.get("ai_group_no"),
        "last_update_date": p.get("last_update_date"),
    }


def _ingredient(a: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ingredient": a.get("ingredient_name"),
        "strength": a.get("strength"),
        "strength_unit": a.get("strength_unit"),
        "dosage_value": a.get("dosage_value") or None,
        "dosage_unit": a.get("dosage_unit") or None,
    }


def _whole(arguments: Dict[str, Any], key: str, default: int, minimum: int) -> int:
    value = arguments.get(key)
    if value is None or value == "":
        return default
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = minimum - 1
    if isinstance(value, bool) or number < minimum:
        raise _DPDError(f"{key} must be an integer of at least {minimum}")
    return number


def _limit(arguments: Dict[str, Any], default: int, maximum: int) -> int:
    return min(_whole(arguments, "limit", default, 1), maximum)


@register_tool("HealthCanadaDPDTool")
class HealthCanadaDPDTool(BaseTool):
    """
    Query the Health Canada Drug Product Database.

    Operations (``fields.operation`` in the tool config):

    - ``search_products``: products by brand name or DIN.
    - ``search_by_ingredient``: products that contain an active ingredient.
    - ``get_product``: one product's ingredients, status, forms, routes,
      schedules and ATC code.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_products"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Run the configured DPD operation."""
        arguments = arguments or {}
        operations = {
            "search_products": self._search_products,
            "search_by_ingredient": self._search_by_ingredient,
            "get_product": self._get_product,
        }
        handler = operations.get(self.operation)
        if handler is None:
            return {"status": "error", "error": f"Unknown operation: {self.operation}"}
        try:
            return handler(arguments)
        except _DPDError as e:
            return {"status": "error", "error": str(e)}
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Health Canada DPD request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to the Health Canada DPD. Check network.",
            }
        except ValueError:
            return {
                "status": "error",
                "error": "Health Canada DPD returned a non-JSON response",
            }
        except Exception as e:  # never raise out of run()
            return {
                "status": "error",
                "error": f"Error querying Health Canada DPD: {e}",
            }

    # -- HTTP -------------------------------------------------------------

    def _get(self, resource: str, **params: Any) -> Any:
        params = {k: v for k, v in params.items() if v is not None}
        params.update(lang="en", type="json")
        response = requests.get(
            f"{DPD_BASE_URL}/{resource}/", params=params, timeout=self.timeout
        )
        if response.status_code == 404:
            raise _NotFound(resource)
        if response.status_code >= 400:
            raise _DPDError(
                f"Health Canada DPD returned HTTP {response.status_code} for {resource}"
            )
        return response.json()

    def _get_list(self, resource: str, **params: Any) -> List[Dict[str, Any]]:
        """A sub-resource as a list; 404 (no entry) is an empty list."""
        try:
            payload = self._get(resource, **params)
        except _NotFound:
            return []
        if isinstance(payload, dict):
            payload = [payload]
        return [
            row
            for row in payload or []
            if isinstance(row, dict) and row.get("drug_code")
        ]

    def _product(self, drug_code: int) -> Optional[Dict[str, Any]]:
        """The product record, or None when the code is unknown."""
        try:
            payload = self._get("drugproduct", id=drug_code)
        except _NotFound:
            return None
        if isinstance(payload, list):
            payload = payload[0] if payload else {}
        if not isinstance(payload, dict) or not payload.get("drug_code"):
            return None  # unknown codes come back as drug_code 0, all null
        return payload

    def _marketed_products(self) -> Dict[int, Dict[str, Any]]:
        """Every marketed product by drug_code; kept for an hour."""
        with _marketed_lock:
            if (
                _marketed["products"] is not None
                and time.time() - _marketed["fetched"] < MARKETED_TTL_S
            ):
                return _marketed["products"]
        payload = self._get("drugproduct", status=MARKETED_STATUS)
        products = {
            p["drug_code"]: p
            for p in payload or []
            if isinstance(p, dict) and p.get("drug_code")
        }
        with _marketed_lock:
            _marketed.update(products=products, fetched=time.time())
        return products

    @staticmethod
    def _metadata(**extra: Any) -> Dict[str, Any]:
        metadata = {"source": "Health Canada Drug Product Database (DPD)"}
        metadata.update({k: v for k, v in extra.items() if v is not None})
        return metadata

    # -- operations -------------------------------------------------------

    def _search_products(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Products by brand name (substring) or DIN."""
        brand = str(arguments.get("brand_name") or "").strip()
        din = str(arguments.get("din") or "").strip()
        if not brand and not din:
            raise _DPDError(
                "Give brand_name (e.g. 'gleevec') or din (8 digits, e.g. '02253275'). "
                "To search by active ingredient use HealthCanadaDPD_search_by_ingredient."
            )
        if din and not (din.isdigit() and len(din) <= 8):
            raise _DPDError("din must be up to 8 digits, e.g. '02253275'")
        limit = _limit(arguments, DEFAULT_LIMIT, MAX_LIMIT)
        marketed = bool(arguments.get("marketed_only"))
        try:
            payload = self._get(
                "drugproduct",
                brandname=brand or None,
                din=din.zfill(8) if din else None,
                status=MARKETED_STATUS if marketed else None,
            )
        except _NotFound:
            payload = []
        if isinstance(payload, dict):
            payload = [payload]
        products = [
            p for p in payload or [] if isinstance(p, dict) and p.get("drug_code")
        ]
        rows = [_product_row(p) for p in products[:limit]]
        return {
            "status": "success",
            "data": rows,
            "metadata": self._metadata(
                brand_name=brand or None,
                din=din or None,
                marketed_only=marketed,
                total_matching=len(products),
                returned=len(rows),
                note=(
                    "Brand names match as substrings and include cancelled "
                    "products unless marketed_only=true. Pass drug_code to "
                    "HealthCanadaDPD_get_product for ingredients, status, form, "
                    "route, schedule and ATC code."
                ),
            ),
        }

    def _search_by_ingredient(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Products that contain an active ingredient (name substring)."""
        ingredient = str(arguments.get("ingredient") or "").strip()
        if not ingredient:
            raise _DPDError("ingredient is required, e.g. 'imatinib'")
        marketed_only = bool(arguments.get("marketed_only"))
        # Marketed rows come from the cached marketed list, so they cost no
        # extra call and may be more; other rows cost one product lookup each.
        maximum = MAX_LIMIT if marketed_only else INGREDIENT_MAX_LIMIT
        limit = _limit(arguments, INGREDIENT_DEFAULT_LIMIT, maximum)
        offset = _whole(arguments, "offset", 0, 0)
        try:
            payload = self._get("activeingredient", ingredientname=ingredient)
        except _NotFound:
            payload = []
        if isinstance(payload, dict):
            payload = [payload]
        # One row per ingredient per product; a combination product has several.
        # The API repeats some rows (drug_code 15609), so duplicates are dropped.
        by_code: Dict[int, List[Dict[str, Any]]] = {}
        for row in payload or []:
            if isinstance(row, dict) and row.get("drug_code"):
                kept = by_code.setdefault(row["drug_code"], [])
                ingredient_row = _ingredient(row)
                if ingredient_row not in kept:
                    kept.append(ingredient_row)
        codes = sorted(by_code)
        marketed: Dict[int, Dict[str, Any]] = {}
        if marketed_only:
            marketed = self._marketed_products()
            codes = [code for code in codes if code in marketed]
        page = codes[offset : offset + limit]
        rows = []
        for code in page:
            if marketed_only:
                product = marketed[code]
            else:
                product = self._product(code) or {"drug_code": code}
            row = _product_row(product)
            row["matched_ingredients"] = by_code[code]
            rows.append(row)
        next_offset = offset + len(page)
        return {
            "status": "success",
            "data": rows,
            "metadata": self._metadata(
                ingredient=ingredient,
                marketed_only=marketed_only,
                total_products=len(codes),
                returned=len(rows),
                offset=offset,
                next_offset=next_offset if next_offset < len(codes) else None,
                note=(
                    "Ingredient names match as substrings ('imatinib' also "
                    "finds 'IMATINIB (IMATINIB MESYLATE)'). Rows are in drug_code "
                    "order, lowest first, and include cancelled products unless "
                    "marketed_only=true. Page with offset (metadata.next_offset)."
                ),
            ),
        }

    def _get_product(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """One product's full record, from its drug_code or DIN."""
        code = arguments.get("drug_code")
        din = str(arguments.get("din") or "").strip()
        if code in (None, "") and not din:
            raise _DPDError(
                "Give drug_code (from a HealthCanadaDPD search) or din (8 digits)."
            )
        if din and not (din.isdigit() and len(din) <= 8):
            raise _DPDError("din must be up to 8 digits, e.g. '02253275'")
        if code in (None, ""):
            try:
                found = self._get("drugproduct", din=din.zfill(8))
            except _NotFound:
                found = []
            found = [
                p for p in found or [] if isinstance(p, dict) and p.get("drug_code")
            ]
            if not found:
                raise _DPDError(f"No Health Canada DPD product with DIN {din}")
            code = found[0]["drug_code"]
        try:
            code = int(code)
        except (TypeError, ValueError):
            raise _DPDError("drug_code must be an integer, e.g. 73824")
        product = self._product(code)
        if product is None:
            raise _DPDError(f"No Health Canada DPD product with drug_code {code}")
        product_din = product.get("drug_identification_number")
        if din and product_din and product_din != din.zfill(8):
            raise _DPDError(
                f"drug_code {code} is DIN {product_din}, not DIN {din}. "
                "Give one of them."
            )

        statuses = self._get_list("status", id=code)
        status = statuses[0] if statuses else {}
        try:
            standard = self._get("pharmaceuticalstd", id=code)
        except _NotFound:
            standard = {}
        data = _product_row(product)
        data.update(
            {
                "active_ingredients": [
                    _ingredient(a) for a in self._get_list("activeingredient", id=code)
                ],
                "status": status.get("status"),
                "status_date": status.get("history_date"),
                "original_market_date": status.get("original_market_date"),
                "dosage_forms": [
                    r.get("pharmaceutical_form_name")
                    for r in self._get_list("form", id=code)
                ],
                "routes": [
                    r.get("route_of_administration_name")
                    for r in self._get_list("route", id=code)
                ],
                "schedules": [
                    r.get("schedule_name") for r in self._get_list("schedule", id=code)
                ],
                "atc": [
                    {"code": r.get("tc_atc_number"), "name": r.get("tc_atc")}
                    for r in self._get_list("therapeuticclass", id=code)
                ],
                "pharmaceutical_standard": (
                    (standard or {}).get("pharmaceutical_std") or None
                    if isinstance(standard, dict)
                    else None
                ),
            }
        )
        return {
            "status": "success",
            "data": data,
            "metadata": self._metadata(drug_code=code),
        }
