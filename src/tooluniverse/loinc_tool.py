"""LOINC API Tool via NIH Clinical Table Search Service.

API: https://clinicaltables.nlm.nih.gov/api/loinc_items/v3/
"""

import requests
from typing import Any, Dict, List
from urllib.parse import urljoin
from .base_tool import BaseTool
from .tool_registry import register_tool

LOINC_BASE_URL = "https://clinicaltables.nlm.nih.gov/api/"


@register_tool("LOINCTool")
class LOINCTool(BaseTool):
    """LOINC tool for lab tests, code details, answer lists, and clinical forms."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.base_url = LOINC_BASE_URL
        self.timeout = 30

    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Any:
        """Make a request to the LOINC Clinical Tables API."""
        url = urljoin(self.base_url, endpoint)
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Failed to query LOINC API: {e}", "endpoint": endpoint}
        except Exception as e:
            return {"error": f"Unexpected error while querying LOINC: {e}", "endpoint": endpoint}

    def _parse_search_results(self, api_response: Any, fields: List[str]) -> Dict[str, Any]:
        """Parse the Clinical Tables response: [total_count, codes, extra_info, data]."""
        if not isinstance(api_response, list) or len(api_response) < 4:
            return {"error": "Invalid API response format", "raw_response": api_response}

        total_count = api_response[0]
        codes = api_response[1] if len(api_response) > 1 else []
        # api_response[2] contains code system info
        data_arrays = api_response[3] if len(api_response) > 3 else []

        results = []
        for i, code in enumerate(codes):
            result_item = {"code": code}

            # Map field data to field names
            if i < len(data_arrays) and data_arrays[i]:
                for j, field_name in enumerate(fields):
                    if j < len(data_arrays[i]):
                        result_item[field_name] = data_arrays[i][j]

            results.append(result_item)

        return {
            "total_count": total_count,
            "count": len(results),
            "results": results
        }

    def _search_loinc_items(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search LOINC lab tests and observations by name or keywords."""
        terms = arguments.get("terms", "").strip()
        if not terms:
            return {"error": "terms parameter is required"}

        max_results = min(arguments.get("max_results", 20), 500)
        exclude_copyrighted = arguments.get("exclude_copyrighted", True)

        # Define fields to retrieve
        fields = ["LOINC_NUM", "LONG_COMMON_NAME", "COMPONENT", "SYSTEM",
                  "SCALE_TYP", "METHOD_TYP", "CLASS"]

        params = {
            "terms": terms,
            "df": ",".join(fields),  # Display fields
            "maxList": max_results,
        }

        if exclude_copyrighted:
            params["excludeCopyrighted"] = "true"

        api_response = self._make_request("loinc_items/v3/search", params)

        if isinstance(api_response, dict) and "error" in api_response:
            return api_response

        parsed = self._parse_search_results(api_response, fields)
        parsed["search_terms"] = terms

        return parsed

    def _get_code_details(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information for a specific LOINC code."""
        loinc_code = arguments.get("loinc_code", "").strip()
        if not loinc_code:
            return {"error": "loinc_code parameter is required"}

        # Get comprehensive fields for details
        fields = ["LOINC_NUM", "LONG_COMMON_NAME", "SHORT_NAME", "COMPONENT",
                  "PROPERTY", "TIME_ASPCT", "SYSTEM", "SCALE_TYP", "METHOD_TYP",
                  "CLASS", "STATUS", "COMMON_TEST_RANK"]

        params = {
            "terms": loinc_code,
            "df": ",".join(fields),
            "maxList": 1,
        }

        api_response = self._make_request("loinc_items/v3/search", params)

        if isinstance(api_response, dict) and "error" in api_response:
            return api_response

        parsed = self._parse_search_results(api_response, fields)

        if parsed.get("count", 0) == 0:
            return {"error": f"No details found for LOINC code: {loinc_code}"}

        # Return the first (and should be only) result
        result = parsed["results"][0] if parsed["results"] else {}
        result["loinc_code"] = loinc_code

        return result

    def _get_answer_list(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get answer list (permissible values) for a LOINC code."""
        loinc_code = arguments.get("loinc_code", "").strip()
        if not loinc_code:
            return {"error": "loinc_code parameter is required"}

        # Use the answer list endpoint
        params = {
            "loinc_num": loinc_code,
        }

        api_response = self._make_request("loinc_answers", params)

        if isinstance(api_response, dict) and "error" in api_response:
            return api_response

        # Parse answer list response
        # Format: [count, [codes], [code_system], [[answer_details]]]
        if not isinstance(api_response, list) or len(api_response) < 4:
            return {
                "error": f"No answer list found for LOINC code: {loinc_code}",
                "loinc_code": loinc_code
            }

        count = api_response[0]
        if count == 0:
            return {
                "error": f"No answer list available for LOINC code: {loinc_code}",
                "loinc_code": loinc_code
            }

        answer_codes = api_response[1] if len(api_response) > 1 else []
        answer_data = api_response[3] if len(api_response) > 3 else []

        answers = []
        for i, code in enumerate(answer_codes):
            answer = {"code": code}
            if i < len(answer_data) and answer_data[i]:
                # Typically includes display text
                if len(answer_data[i]) > 0:
                    answer["display"] = answer_data[i][0]
            answers.append(answer)

        return {
            "loinc_code": loinc_code,
            "answer_count": count,
            "answers": answers
        }

    def _search_forms(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search LOINC forms and survey instruments (e.g., PHQ-9, GAD-7)."""
        terms = arguments.get("terms", "").strip()
        if not terms:
            return {"error": "terms parameter is required"}

        max_results = min(arguments.get("max_results", 20), 200)

        # Search in LOINC forms/panels
        fields = ["LOINC_NUM", "LONG_COMMON_NAME", "CLASS", "STATUS"]

        params = {
            "terms": terms,
            "df": ",".join(fields),
            "maxList": max_results,
            "sf": "CLASS",  # Search in CLASS field
        }

        api_response = self._make_request("loinc_items/v3/search", params)

        if isinstance(api_response, dict) and "error" in api_response:
            return api_response

        parsed = self._parse_search_results(api_response, fields)

        # Filter for forms/panels (CLASS typically contains "Survey" or "Panel")
        if "results" in parsed:
            forms = []
            for item in parsed["results"]:
                class_field = item.get("CLASS", "").lower()
                if "survey" in class_field or "panel" in class_field or "form" in class_field:
                    forms.append(item)

            parsed["results"] = forms
            parsed["count"] = len(forms)

        parsed["search_terms"] = terms

        return parsed

    _OPERATION_MAP = {
        "search_tests": "_search_loinc_items",
        "get_code_details": "_get_code_details",
        "get_answer_list": "_get_answer_list",
        "search_forms": "_search_forms",
    }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the LOINC tool based on the operation derived from tool config name."""
        tool_name = self.tool_config.get("name", "")

        for key, method_name in self._OPERATION_MAP.items():
            if key in tool_name:
                return getattr(self, method_name)(arguments)

        return {"error": f"Unknown operation for tool: {tool_name}"}
