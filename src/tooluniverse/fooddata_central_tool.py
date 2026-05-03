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
            status_code = e.response.status_code if e.response else "unknown"
            detail = ""
            if e.response is not None:
                detail = e.response.text[:200]
            if status_code == 403:
                return {
                    "status": "error",
                    "error": "FoodData Central API key invalid or missing. Set FDC_API_KEY env variable.",
                }
            elif status_code == 429:
                return {
                    "status": "error",
                    "error": "FoodData Central rate limit exceeded (1000 req/hr). Try again later.",
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
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        params = {"query": query}
        if "page_size" in arguments:
            params["pageSize"] = arguments["page_size"]
        if "page_number" in arguments:
            params["pageNumber"] = arguments["page_number"]
        if "data_type" in arguments:
            params["dataType"] = arguments["data_type"]

        response = self._make_get_request("foods/search", params)
        data = response.json()

        # Extract food results with key fields
        foods = []
        for food in data.get("foods", []):
            food_item = {
                "fdcId": food.get("fdcId"),
                "description": food.get("description"),
                "dataType": food.get("dataType"),
                "brandOwner": food.get("brandOwner", ""),
                "ingredients": food.get("ingredients", ""),
                "servingSize": food.get("servingSize"),
                "servingSizeUnit": food.get("servingSizeUnit", ""),
            }
            # Include top nutrients
            nutrients = []
            for n in food.get("foodNutrients", [])[:10]:
                nutrients.append(
                    {
                        "name": n.get("nutrientName", ""),
                        "value": n.get("value"),
                        "unit": n.get("unitName", ""),
                    }
                )
            food_item["topNutrients"] = nutrients
            foods.append(food_item)

        return {
            "status": "success",
            "data": foods,
            "metadata": {
                "totalHits": data.get("totalHits", 0),
                "currentPage": data.get("currentPage", 1),
                "totalPages": data.get("totalPages", 0),
                "source": "USDA FoodData Central",
            },
        }

    def _get_food_detail(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed food information by FDC ID."""
        fdc_id = arguments.get("fdc_id")
        if not fdc_id:
            return {"status": "error", "error": "fdc_id parameter is required"}

        response = self._make_get_request(f"food/{fdc_id}")
        data = response.json()

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
