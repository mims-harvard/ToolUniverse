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
                "off_market": bool(payload.get("offMarket")),
            },
            "metadata": {
                "product_id": product_id,
                "ingredient_count": len(payload.get("ingredientRows") or []),
                "note": "percent_daily_value is null where no daily value is "
                "established for that ingredient.",
                "source": "NIH Dietary Supplement Label Database (DSLD)",
            },
        }
