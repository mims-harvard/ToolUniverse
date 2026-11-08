# nih_dsld_tool.py
"""
NIH Dietary Supplement Label Database (DSLD) tool for ToolUniverse.

DSLD holds machine-readable label data for over 200,000 dietary supplement
products sold in the US: every ingredient with its per-serving amount, unit,
and percent daily value, plus brand, product type, and market status.

ToolUniverse has ~150 tools reading FDA drug labels, but supplements are a
separate regulatory category (no FDA premarket approval) with no coverage
at all today. This tool closes that gap.

API: https://api.ods.od.nih.gov/dsld/v9
No authentication required.
"""

from typing import Dict, Any, List

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

DSLD_BASE_URL = "https://api.ods.od.nih.gov/dsld/v9"


def _flatten_ingredients(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flatten DSLD's nested ingredient rows into one list per serving amount."""
    flat: List[Dict[str, Any]] = []
    for row in rows:
        quantities = row.get("quantity") or [{}]
        for qty in quantities:
            flat.append(
                {
                    "name": row.get("name"),
                    "category": row.get("category"),
                    "amount": qty.get("quantity"),
                    "unit": qty.get("unit"),
                    "percent_daily_value": next(
                        (
                            g.get("percent")
                            for g in qty.get("dailyValueTargetGroup") or []
                            if g.get("percent") is not None
                        ),
                        None,
                    ),
                    "per_serving_quantity": qty.get("servingSizeQuantity"),
                    "per_serving_unit": qty.get("servingSizeUnit"),
                    "notes": row.get("notes"),
                }
            )
        for nested in row.get("nestedRows") or []:
            flat.extend(_flatten_ingredients([nested]))
    return flat


# Label statements and other ingredients per product. The audited gummy label
# carries 23 statements and 9 other ingredients, so the caps guard an
# outlier rather than cutting a normal label.
STATEMENTS_PER_LABEL = 60
OTHER_INGREDIENTS_PER_LABEL = 60


def _statements(payload: dict) -> list:
    """The text printed on the label, under the type that says what it is.

    A tool that promises "one dietary supplement's full label" returned the
    ingredient table and none of the statements. The audited label's 23
    include "Precautions re: Pregnant or Nursing or Prescription
    Medications", "Precautions re: Children", "Suggested/Recommended/Usage/
    Directions", "Storage" and the FDA disclaimer. Without `type`, a
    precaution reads like a marketing line.
    """
    out = []
    for statement in payload.get("statements") or []:
        if not isinstance(statement, dict):
            continue
        text = (statement.get("notes") or "").strip()
        if not text and not statement.get("type"):
            continue
        out.append({"type": statement.get("type"), "text": text or None})
        if len(out) >= STATEMENTS_PER_LABEL:
            break
    return out


def _other_ingredients(payload: dict) -> dict:
    """The inactive ingredients, which are half of "every ingredient"."""
    block = payload.get("otheringredients") or {}
    if not isinstance(block, dict):
        return {"text": None, "ingredients": [], "ingredient_count": 0}
    rows = []
    for ingredient in block.get("ingredients") or []:
        if not isinstance(ingredient, dict):
            continue
        rows.append(
            {
                "name": ingredient.get("name"),
                "category": ingredient.get("category"),
                "ingredient_group": ingredient.get("ingredientGroup"),
                "unii_code": ingredient.get("uniiCode"),
                "alternate_names": [
                    n for n in (ingredient.get("alternateNames") or []) if n
                ],
            }
        )
        if len(rows) >= OTHER_INGREDIENTS_PER_LABEL:
            break
    return {
        "text": (block.get("text") or None),
        "ingredients": rows,
        "ingredient_count": len(block.get("ingredients") or []),
    }


def _contacts(payload: dict) -> list:
    """Who makes or distributes the product, as printed on the label."""
    out = []
    for contact in payload.get("contacts") or []:
        if not isinstance(contact, dict):
            continue
        details = contact.get("contactDetails") or {}
        out.append(
            {
                "role": contact.get("text"),
                "types": [t for t in (contact.get("types") or []) if t],
                "name": details.get("name"),
                "city": details.get("city") or None,
                "state": details.get("state") or None,
                "country": details.get("country") or None,
                "web_address": details.get("webAddress") or None,
            }
        )
    return out


@register_tool("NIHDSLDTool")
class NIHDSLDTool(BaseTool):
    """
    Tool for querying the NIH Dietary Supplement Label Database.

    Supports searching supplement products by name or ingredient, and
    fetching one product's full label: ingredients with per-serving amounts
    and percent daily values.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 45)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_products"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the DSLD lookup."""
        try:
            if self.operation == "search_products":
                return self._search_products(arguments)
            if self.operation == "get_label":
                return self._get_label(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DSLD request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to DSLD. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"DSLD returned HTTP {code}"}
        except ValueError:
            return {"status": "error", "error": "DSLD returned a non-JSON response"}
        except Exception as e:
            return {"status": "error", "error": f"Error querying DSLD: {str(e)}"}

    def _search_products(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search supplement products by name or ingredient."""
        query = (arguments.get("query") or "").strip()
        if not query:
            return {
                "status": "error",
                "error": "query is required: a product name, brand, or "
                "ingredient, e.g. 'vitamin d' or 'turmeric'.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 25
        limit = min(limit, 100)

        response = requests.get(
            f"{DSLD_BASE_URL}/search-filter",
            params={"q": query, "size": limit},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        hits = payload.get("hits") or []

        rows = []
        for hit in hits:
            source = hit.get("_source") or {}
            net_contents = source.get("netContents") or []
            rows.append(
                {
                    "product_id": hit.get("_id"),
                    "name": source.get("fullName"),
                    "brand": source.get("brandName"),
                    "product_type": (source.get("productType") or {}).get(
                        "langualCodeDescription"
                    ),
                    "physical_state": (source.get("physicalState") or {}).get(
                        "langualCodeDescription"
                    ),
                    "net_contents": net_contents[0].get("display")
                    if net_contents
                    else None,
                    "off_market": bool(source.get("offMarket")),
                }
            )

        if not rows:
            return {
                "status": "error",
                "error": f"No DSLD products matching '{query}'.",
            }

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "query": query,
                "total_matching": (payload.get("stats") or {}).get("count"),
                "returned": len(rows),
                "note": "product_id is what get_label expects for the full "
                "ingredient list.",
                "source": "NIH Dietary Supplement Label Database (DSLD)",
            },
        }

    def _get_label(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch one product's full label: ingredients and serving size."""
        product_id = arguments.get("product_id")
        if product_id is None or str(product_id).strip() == "":
            return {
                "status": "error",
                "error": "product_id is required. Use NIHDSLD_search_products "
                "to find one by name.",
            }

        product_id = str(product_id).strip()
        response = requests.get(
            f"{DSLD_BASE_URL}/label/{product_id}", timeout=self.timeout
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not payload.get("fullName"):
            return {
                "status": "error",
                "error": f"No DSLD product with id '{product_id}'.",
            }

        serving_sizes = payload.get("servingSizes") or []

        return {
            "status": "success",
            "data": {
                "product_id": payload.get("id"),
                "name": payload.get("fullName"),
                "brand": payload.get("brandName"),
                "upc": payload.get("upcSku"),
                "product_type": (payload.get("productType") or {}).get(
                    "langualCodeDescription"
                ),
                "serving_size": serving_sizes[0] if serving_sizes else None,
                "servings_per_container": payload.get("servingsPerContainer"),
                "ingredients": _flatten_ingredients(
                    payload.get("ingredientRows") or []
                ),
                # The other half of "every ingredient": the inactive ones.
                "other_ingredients": _other_ingredients(payload),
                # What the package says, with the type that says what kind of
                # statement it is -- precaution, directions, storage.
                "statements": _statements(payload),
                "net_contents": [
                    {
                        "quantity": entry.get("quantity"),
                        "unit": entry.get("unit"),
                        "display": entry.get("display"),
                    }
                    for entry in (payload.get("netContents") or [])
                    if isinstance(entry, dict)
                ],
                # What the percent_daily_value above is a percentage OF.
                "percent_dv_footnote": payload.get("percentDvFootnote") or None,
                "claim_types": [
                    claim.get("langualCodeDescription")
                    for claim in (payload.get("claims") or [])
                    if isinstance(claim, dict) and claim.get("langualCodeDescription")
                ],
                "contacts": _contacts(payload),
                "off_market": bool(payload.get("offMarket")),
                # off_market says whether; the events say when.
                "events": [
                    {"date": event.get("date"), "type": event.get("type")}
                    for event in (payload.get("events") or [])
                    if isinstance(event, dict)
                ],
                "pdf_url": payload.get("pdf") or None,
            },
            "metadata": {
                "product_id": product_id,
                "ingredient_count": len(payload.get("ingredientRows") or []),
                "statement_count": len(payload.get("statements") or []),
                "statements_per_label": STATEMENTS_PER_LABEL,
                "other_ingredients_per_label": OTHER_INGREDIENTS_PER_LABEL,
                "note": "percent_daily_value is null where no daily value is "
                "established for that ingredient; percent_dv_footnote says "
                "what the percentages are based on.",
                "source": "NIH Dietary Supplement Label Database (DSLD)",
            },
        }
