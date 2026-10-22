# fooddata_central_tool.py
"""
USDA FoodData Central API tool for ToolUniverse.

FoodData Central (FDC) is the U.S. Department of Agriculture's comprehensive
food composition database providing nutrient data for over 1 million foods.

API Documentation: https://fdc.nal.usda.gov/api-guide/
OpenAPI Spec: https://fdc.nal.usda.gov/api-spec/fdc_api.html
"""

import requests
import os
import math
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for USDA FoodData Central API
FDC_BASE_URL = "https://api.nal.usda.gov/fdc/v1"


@register_tool("FoodDataCentralTool")
class FoodDataCentralTool(BaseTool):
    """
    Tool for querying the USDA FoodData Central API.

    FoodData Central provides comprehensive food and nutrient data including:
    - Food search by name/keyword
    - Detailed food nutrient profiles
    - Food listing with pagination
    - Multiple data types: Foundation, SR Legacy, Branded, Survey (FNDDS)

    Authentication: Requires a free API key from data.gov.
    Rate limit: 1,000 requests per hour per IP address.
    Set the FDC_API_KEY environment variable, or use 'DEMO_KEY' for testing.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        # Get the operation type from config
        self.operation = tool_config.get("fields", {}).get("operation", "search")
        # API key from environment (DEMO_KEY as fallback for testing)
        self.api_key = os.environ.get("FDC_API_KEY", "DEMO_KEY")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the FoodData Central API call based on the configured operation."""
        operation = self.operation

        try:
            if operation == "search":
                return self._search_foods(arguments)
            elif operation == "detail":
                return self._get_food_detail(arguments)
            elif operation == "list":
                return self._list_foods(arguments)
            elif operation == "nutrients":
                return self._get_food_nutrients(arguments)
            else:
                return {"status": "error", "error": f"Unknown operation: {operation}"}
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"FoodData Central API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to FoodData Central API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            # Fix-R15A-1: requests.Response overrides __bool__ to return
            # self.ok, which is False for any 4xx/5xx status -- so
            # `if e.response else "unknown"` was always false-y for a real
            # HTTP error response (confirmed live), making the 403/429
            # branches below unreachable dead code. Use `is not None`.
            status_code = (
                e.response.status_code if e.response is not None else "unknown"
            )
            detail = ""
            if e.response is not None:
                detail = e.response.text[:200]
            if status_code == 403:
                return {
                    "status": "error",
                    "error": "FoodData Central API key invalid or missing. Set FDC_API_KEY env variable.",
                }
            elif status_code == 429:
                key_hint = (
                    " (using the shared DEMO_KEY -- get a free personal key at "
                    "https://api.nal.usda.gov/signup/ and set FDC_API_KEY for a "
                    "higher limit)"
                    if self.api_key == "DEMO_KEY"
                    else ""
                )
                return {
                    "status": "error",
                    "error": f"FoodData Central rate limit exceeded (1000 req/hr){key_hint}. Try again later.",
                }
            return {
                "status": "error",
                "error": f"FoodData Central API HTTP error {status_code}: {detail}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying FoodData Central: {str(e)}",
            }

    def _make_get_request(
        self, endpoint: str, params: Dict[str, Any] = None
    ) -> requests.Response:
        """Make a GET request to FDC API with authentication."""
        if params is None:
            params = {}
        params["api_key"] = self.api_key
        url = f"{FDC_BASE_URL}/{endpoint}"
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response

    def _search_foods(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for foods by keyword/query string."""
        query = arguments.get("query", "")
        if not isinstance(query, str) or not query.strip():
            return {"status": "error", "error": "query must be a non-empty string"}
        query = query.strip()

        page_size = arguments.get("page_size", 25)
        page_number = arguments.get("page_number", 1)
        if (
            isinstance(page_size, bool)
            or not isinstance(page_size, int)
            or not 1 <= page_size <= 200
        ):
            return {
                "status": "error",
                "error": "page_size must be an integer from 1 to 200",
            }
        if (
            isinstance(page_number, bool)
            or not isinstance(page_number, int)
            or page_number < 1
        ):
            return {
                "status": "error",
                "error": "page_number must be a positive integer",
            }
        data_type = arguments.get("data_type")
        allowed_data_types = {
            "Foundation",
            "Branded",
            "SR Legacy",
            "Survey (FNDDS)",
        }
        if data_type is not None and data_type not in allowed_data_types:
            return {
                "status": "error",
                "error": "data_type is not a supported FoodData Central data type",
            }

        params = {"query": query, "pageSize": page_size, "pageNumber": page_number}
        if data_type is not None:
            params["dataType"] = data_type

        response = self._make_get_request("foods/search", params)
        data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get("foods"), list):
            return {
                "status": "error",
                "error": "FoodData Central search response lacked a foods array",
            }
        total_hits = data.get("totalHits")
        current_page = data.get("currentPage")
        total_pages = data.get("totalPages")
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in (total_hits, current_page, total_pages)
        ):
            return {
                "status": "error",
                "error": "FoodData Central returned invalid pagination metadata",
            }
        if current_page != page_number:
            return {
                "status": "error",
                "error": "FoodData Central returned a different page than requested",
                "requested_page": page_number,
                "returned_page": current_page,
            }

        raw_foods = data["foods"]
        expected_pages = math.ceil(total_hits / page_size) if total_hits else 0
        if total_pages != expected_pages:
            return {
                "status": "error",
                "error": "FoodData Central pagination totals were internally inconsistent",
                "total_hits": total_hits,
                "page_size": page_size,
                "reported_total_pages": total_pages,
                "expected_total_pages": expected_pages,
            }

        # Extract food results with key fields
        foods = []
        for food in raw_foods:
            if not isinstance(food, dict) or not isinstance(
                food.get("foodNutrients"), list
            ):
                return {
                    "status": "error",
                    "error": "FoodData Central returned a malformed food or nutrient array",
                }
            food_item = {
                "fdcId": food.get("fdcId"),
                "description": food.get("description"),
                "dataType": food.get("dataType"),
                "brandOwner": food.get("brandOwner", ""),
                "ingredients": food.get("ingredients", ""),
                "servingSize": food.get("servingSize"),
                "servingSizeUnit": food.get("servingSizeUnit", ""),
            }
            # Preserve the historical first-10 summary, but also expose the
            # complete nutrient list returned by USDA. The API does not rank
            # this array, so the first ten must not be treated as exhaustive.
            nutrients = []
            for n in food["foodNutrients"]:
                if not isinstance(n, dict):
                    return {
                        "status": "error",
                        "error": "FoodData Central returned a malformed nutrient entry",
                    }
                nutrients.append(
                    {
                        "name": n.get("nutrientName", ""),
                        "value": n.get("value"),
                        "unit": n.get("unitName", ""),
                    }
                )
            food_item["nutrients"] = nutrients
            food_item["nutrientCount"] = len(nutrients)
            food_item["topNutrients"] = nutrients[:10]
            foods.append(food_item)

        has_more = current_page < total_pages
        remaining = max(total_hits - ((current_page - 1) * page_size), 0)
        expected_returned = min(page_size, remaining)
        count_matches = len(foods) == expected_returned
        stalled = not count_matches
        return {
            "status": "success",
            "data": foods,
            "metadata": {
                "totalHits": total_hits,
                "currentPage": current_page,
                "totalPages": total_pages,
                "returned": len(foods),
                "expectedReturned": expected_returned,
                "returnedCountMatchesMetadata": count_matches,
                "pageSize": page_size,
                "hasMore": has_more,
                "nextPage": current_page + 1 if has_more and count_matches else None,
                "requestedPageComplete": count_matches,
                "resultSetComplete": current_page == 1
                and not has_more
                and count_matches,
                "paginationStalled": stalled,
                "source": "USDA FoodData Central",
            },
        }

    def _get_food_detail(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed food information by FDC ID."""
        fdc_id = arguments.get("fdc_id")
        if isinstance(fdc_id, bool) or not isinstance(fdc_id, int) or fdc_id < 1:
            return {"status": "error", "error": "fdc_id must be a positive integer"}

        response = self._make_get_request(f"food/{fdc_id}")
        data = response.json()
        if not isinstance(data, dict) or data.get("fdcId") != fdc_id:
            return {
                "status": "error",
                "error": "FoodData Central detail response did not match requested fdc_id",
                "requested_fdc_id": fdc_id,
                "returned_fdc_id": data.get("fdcId")
                if isinstance(data, dict)
                else None,
            }
        if not isinstance(data.get("foodNutrients"), list):
            return {
                "status": "error",
                "error": "FoodData Central detail response lacked foodNutrients",
            }

        # Structure the response
        result = {
            "fdcId": data.get("fdcId"),
            "description": data.get("description"),
            "dataType": data.get("dataType"),
            "publicationDate": data.get("publicationDate"),
            "brandOwner": data.get("brandOwner", ""),
            "ingredients": data.get("ingredients", ""),
            "servingSize": data.get("servingSize"),
            "servingSizeUnit": data.get("servingSizeUnit", ""),
        }

        # Extract all nutrients
        nutrients = []
        for fn in data.get("foodNutrients", []):
            nutrient_info = fn.get("nutrient", fn)
            nutrients.append(
                {
                    "name": nutrient_info.get("name", fn.get("nutrientName", "")),
                    "number": nutrient_info.get("number", fn.get("nutrientNumber", "")),
                    "amount": fn.get("amount", fn.get("value")),
                    "unit": nutrient_info.get("unitName", fn.get("unitName", "")),
                }
            )
        result["nutrients"] = nutrients

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "nutrient_count": len(nutrients),
                "source": "USDA FoodData Central",
            },
        }

    def _list_foods(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List foods in abridged format with pagination."""
        params = {}
        if "page_size" in arguments:
            params["pageSize"] = arguments["page_size"]
        if "page_number" in arguments:
            params["pageNumber"] = arguments["page_number"]
        if "data_type" in arguments:
            params["dataType"] = arguments["data_type"]
        if "sort_by" in arguments:
            params["sortBy"] = arguments["sort_by"]
        if "sort_order" in arguments:
            params["sortOrder"] = arguments["sort_order"]

        response = self._make_get_request("foods/list", params)
        data = response.json()

        # Structure the list response
        foods = []
        if isinstance(data, list):
            for food in data:
                foods.append(
                    {
                        "fdcId": food.get("fdcId"),
                        "description": food.get("description"),
                        "dataType": food.get("dataType"),
                        "publicationDate": food.get("publicationDate", ""),
                    }
                )
        return {
            "status": "success",
            "data": foods,
            "metadata": {"count": len(foods), "source": "USDA FoodData Central"},
        }

    def _get_food_nutrients(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get only nutrients for a food by FDC ID (detailed nutrient profile)."""
        fdc_id = arguments.get("fdc_id")
        if not fdc_id:
            return {"status": "error", "error": "fdc_id parameter is required"}

        response = self._make_get_request(f"food/{fdc_id}")
        data = response.json()

        nutrients = []
        for fn in data.get("foodNutrients", []):
            nutrient_info = fn.get("nutrient", fn)
            amount = fn.get("amount", fn.get("value"))
            if amount is not None:
                nutrients.append(
                    {
                        "name": nutrient_info.get("name", fn.get("nutrientName", "")),
                        "number": nutrient_info.get(
                            "number", fn.get("nutrientNumber", "")
                        ),
                        "amount": amount,
                        "unit": nutrient_info.get("unitName", fn.get("unitName", "")),
                    }
                )

        return {
            "status": "success",
            "data": {
                "fdcId": data.get("fdcId"),
                "description": data.get("description"),
                "nutrients": sorted(nutrients, key=lambda x: x.get("name", "")),
            },
            "metadata": {
                "nutrient_count": len(nutrients),
                "source": "USDA FoodData Central",
            },
        }
