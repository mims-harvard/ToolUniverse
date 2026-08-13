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
            return {
                "status": "error",
                "error": f"Failed to query LOINC API: {e}",
                "endpoint": endpoint,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error while querying LOINC: {e}",
                "endpoint": endpoint,
            }

    # Fields the loinc_items/v3 index does NOT carry, probed field-by-field
    # against the live API on 2026-08-13 with
    # `search?terms=2823-3&df=<FIELD>`:
    #
    #   COMPONENT           -> "Potassium"
    #   PROPERTY            -> "SCnc"
    #   LONG_COMMON_NAME    -> "Potassium [Moles/volume] in Serum or Plasma"
    #   SHORTNAME           -> "Potassium SerPl-sCnc"
    #   SYSTEM, SCALE_TYP, CLASS, STATUS, TIME_ASPCT, METHOD_TYP,
    #   COMMON_TEST_RANK  -> "" for every one
    #
    # (CLASSTYPE and ORDER_OBS are equally empty upstream but this module never
    # requests them, so they are not listed below -- the tuple describes fields
    # this tool actually asks for.)
    #
    # Fix-R48: these were requested anyway and emitted as empty strings, so
    # LOINC 2823-3 -- serum potassium, about the most-ordered test there is --
    # came back with SYSTEM "", SCALE_TYP "" and CLASS "". Those are exactly
    # the fields that separate serum potassium from urine potassium or a
    # potassium clearance, so a rule author choosing a code was shown a blank
    # where the discriminating value should be, with nothing saying the index
    # simply does not publish it. An unavailable field was presented as a valid
    # empty answer.
    _FIELDS_ABSENT_FROM_V3_INDEX = (
        "SYSTEM",
        "SCALE_TYP",
        "METHOD_TYP",
        "CLASS",
        "STATUS",
        "TIME_ASPCT",
        "COMMON_TEST_RANK",
    )

    _UNAVAILABLE_FIELDS_NOTE = (
        "The clinicaltables loinc_items/v3 index does not publish these "
        "fields, so they are returned empty for every code and their "
        "emptiness carries no information about this code: {fields}. Use the "
        "full LOINC release or a FHIR terminology server if you need to "
        "select a code on them."
    )

    # Added only when SYSTEM is among the absent fields, since it is the one
    # whose absence changes which code a caller should pick.
    _SPECIMEN_CAVEAT = (
        " SYSTEM (specimen) in particular is unavailable, so this response "
        "cannot distinguish e.g. a serum from a urine measurement."
    )

    @classmethod
    def _unavailable_fields_disclosure(cls, fields: List[str]) -> Dict[str, Any]:
        """Name the requested fields this index cannot answer, or {} if none."""
        absent = [f for f in fields if f in cls._FIELDS_ABSENT_FROM_V3_INDEX]
        if not absent:
            return {}
        note = cls._UNAVAILABLE_FIELDS_NOTE.format(fields=", ".join(absent))
        if "SYSTEM" in absent:
            note += cls._SPECIMEN_CAVEAT
        return {"fields_unavailable": absent, "fields_unavailable_note": note}

    @staticmethod
    def _is_api_error(api_response: Any) -> bool:
        """Check if an API response is an error dict."""
        return isinstance(api_response, dict) and "error" in api_response

    def _parse_search_results(
        self, api_response: Any, fields: List[str]
    ) -> Dict[str, Any]:
        """Parse the Clinical Tables response: [total_count, codes, extra_info, data]."""
        if not isinstance(api_response, list) or len(api_response) < 4:
            return {
                "status": "error",
                "error": "Invalid API response format",
                "raw_response": api_response,
            }

        total_count = api_response[0]
        codes = api_response[1] if len(api_response) > 1 else []
        data_arrays = api_response[3] if len(api_response) > 3 else []

        results = []
        for i, code in enumerate(codes):
            result_item = {"code": code}
            if i < len(data_arrays) and data_arrays[i]:
                for field_name, value in zip(fields, data_arrays[i]):
                    result_item[field_name] = value
            results.append(result_item)

        parsed = {
            "total_count": total_count,
            "count": len(results),
            "results": results,
        }
        # Attached here rather than per operation: every operation funnels
        # through this method with the field list it requested, so all four are
        # covered and none can be added later without the disclosure.
        parsed.update(self._unavailable_fields_disclosure(fields))
        return parsed

    def _search_loinc_items(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search LOINC lab tests and observations by name or keywords."""
        terms = arguments.get("terms", "").strip()
        if not terms:
            return {"status": "error", "error": "terms parameter is required"}

        max_results = min(arguments.get("max_results", 20), 500)
        exclude_copyrighted = arguments.get("exclude_copyrighted", True)

        # Define fields to retrieve
        fields = [
            "LOINC_NUM",
            "LONG_COMMON_NAME",
            "COMPONENT",
            "SYSTEM",
            "SCALE_TYP",
            "METHOD_TYP",
            "CLASS",
        ]

        params = {
            "terms": terms,
            "df": ",".join(fields),  # Display fields
            "maxList": max_results,
        }

        if exclude_copyrighted:
            params["excludeCopyrighted"] = "true"

        api_response = self._make_request("loinc_items/v3/search", params)

        if self._is_api_error(api_response):
            return api_response

        parsed = self._parse_search_results(api_response, fields)
        parsed["search_terms"] = terms

        return parsed

    def _get_code_details(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information for a specific LOINC code."""
        loinc_code = arguments.get("loinc_code", "").strip()
        if not loinc_code:
            return {"status": "error", "error": "loinc_code parameter is required"}

        # Get comprehensive fields for details
        fields = [
            "LOINC_NUM",
            "LONG_COMMON_NAME",
            # Fix-R48: this was "SHORT_NAME", which the v3 index does not
            # recognise, so it answered "" for every code in existence. The
            # index spells it SHORTNAME -- verified live, df=SHORT_NAME returns
            # [1,["2823-3"],null,[[""]]] while df=SHORTNAME returns
            # [1,["2823-3"],null,[["Potassium SerPl-sCnc"]]].
            "SHORTNAME",
            "COMPONENT",
            "PROPERTY",
            "TIME_ASPCT",
            "SYSTEM",
            "SCALE_TYP",
            "METHOD_TYP",
            "CLASS",
            "STATUS",
            "COMMON_TEST_RANK",
        ]

        params = {
            "terms": loinc_code,
            "df": ",".join(fields),
            "maxList": 1,
        }

        api_response = self._make_request("loinc_items/v3/search", params)

        if self._is_api_error(api_response):
            return api_response

        parsed = self._parse_search_results(api_response, fields)

        if parsed.get("count", 0) == 0:
            return {
                "status": "error",
                "error": f"No details found for LOINC code: {loinc_code}",
            }

        # Return the first (and should be only) result
        result = parsed["results"][0] if parsed["results"] else {}
        result["loinc_code"] = loinc_code
        result.update(self._unavailable_fields_disclosure(fields))

        return result

    def _get_answer_list(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for LOINC answer-type codes matching a search term."""
        loinc_code = arguments.get("loinc_code", "").strip()
        if not loinc_code:
            return {"status": "error", "error": "loinc_code parameter is required"}

        fields = ["LOINC_NUM", "LONG_COMMON_NAME", "COMPONENT", "SCALE_TYP"]

        params = {
            "terms": loinc_code,
            "df": ",".join(fields),
            "maxList": 20,
            "type": "answer",
        }

        api_response = self._make_request("loinc_items/v3/search", params)

        if self._is_api_error(api_response):
            return api_response

        parsed = self._parse_search_results(api_response, fields)

        if parsed.get("count", 0) == 0:
            return {
                "status": "error",
                "error": f"No LOINC answer codes found for: {loinc_code}",
                "loinc_code": loinc_code,
            }

        parsed["query"] = loinc_code
        return parsed

    def _search_forms(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search LOINC forms and survey instruments (e.g., PHQ-9, GAD-7)."""
        terms = arguments.get("terms", "").strip()
        if not terms:
            return {"status": "error", "error": "terms parameter is required"}

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

        if self._is_api_error(api_response):
            return api_response

        parsed = self._parse_search_results(api_response, fields)

        # Filter for forms/panels (CLASS typically contains "Survey" or "Panel")
        if "results" in parsed:
            forms = []
            for item in parsed["results"]:
                class_field = item.get("CLASS", "").lower()
                if (
                    "survey" in class_field
                    or "panel" in class_field
                    or "form" in class_field
                ):
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

        return {"status": "error", "error": f"Unknown operation for tool: {tool_name}"}
