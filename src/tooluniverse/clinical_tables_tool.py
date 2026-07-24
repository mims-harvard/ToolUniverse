"""NCBI/NLM Clinical Table Search Service tools (non-ICD, non-LOINC endpoints).

Covers the Clinical Tables endpoints not already wrapped by ICDTool/LOINCTool:
  - rxterms        → drug-name autocomplete with strengths/forms + RxCUIs
  - conditions     → patient problem-list autocomplete with ICD-10-CM/ICD-9 crosswalk
  - disease_names  → disease-name autocomplete with UMLS CUI

API: https://clinicaltables.nlm.nih.gov/api/<table>/v3/search
Response shape: [total_count, codes, extra_fields_hash_or_null, display_arrays]
"""

import requests
from typing import Any, Dict, List
from urllib.parse import urljoin

from .base_tool import BaseTool
from .tool_registry import register_tool

CLINICAL_TABLES_BASE_URL = "https://clinicaltables.nlm.nih.gov/api/"


@register_tool("ClinicalTablesTool")
class ClinicalTablesTool(BaseTool):
    """Autocomplete/search over NLM Clinical Tables (drugs, conditions, diseases)."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.base_url = CLINICAL_TABLES_BASE_URL
        self.timeout = 30

    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Any:
        url = urljoin(self.base_url, endpoint)
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"Failed to query Clinical Tables API: {e}",
                "endpoint": endpoint,
            }
        except ValueError as e:
            return {
                "status": "error",
                "error": f"Invalid JSON from Clinical Tables API: {e}",
                "endpoint": endpoint,
            }

    @staticmethod
    def _is_api_error(api_response: Any) -> bool:
        return isinstance(api_response, dict) and "error" in api_response

    def _parse(
        self,
        api_response: Any,
        display_fields: List[str],
        extra_fields: List[str],
    ) -> Dict[str, Any]:
        """Parse [total, codes, extra_hash, display_arrays] into row dicts."""
        if not isinstance(api_response, list) or len(api_response) < 4:
            return {
                "status": "error",
                "error": "Invalid API response format",
                "raw_response": api_response,
            }

        total_count = api_response[0]
        codes = api_response[1] or []
        extra_hash = api_response[2] if isinstance(api_response[2], dict) else {}
        display_arrays = api_response[3] or []

        results = []
        for i, code in enumerate(codes):
            row: Dict[str, Any] = {"code": code}
            if i < len(display_arrays) and display_arrays[i]:
                for field_name, value in zip(display_fields, display_arrays[i]):
                    row[field_name] = value
            for field_name in extra_fields:
                values = extra_hash.get(field_name)
                if isinstance(values, list) and i < len(values):
                    row[field_name] = values[i]
            results.append(row)

        return {"total_count": total_count, "count": len(results), "results": results}

    def _search(
        self,
        endpoint: str,
        arguments: Dict[str, Any],
        display_fields: List[str],
        extra_fields: List[str],
        send_df: bool = True,
        max_cap: int = 500,
    ) -> Dict[str, Any]:
        terms = str(arguments.get("terms", "")).strip()
        if not terms:
            return {"status": "error", "error": "terms parameter is required"}

        max_results = min(int(arguments.get("max_results", 20) or 20), max_cap)
        params: Dict[str, Any] = {"terms": terms, "maxList": max_results}
        # Some tables (e.g. disease_names) only populate their name via the default
        # display column and return blanks when an explicit df is requested; for
        # those we omit df and label the default column with display_fields[0].
        if send_df:
            params["df"] = ",".join(display_fields)
        if extra_fields:
            params["ef"] = ",".join(extra_fields)

        api_response = self._make_request(f"{endpoint}/v3/search", params)
        if self._is_api_error(api_response):
            return api_response

        parsed = self._parse(api_response, display_fields, extra_fields)
        parsed["search_terms"] = terms
        return parsed

    def _search_rxterms(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Drug-name autocomplete with available strengths/forms and RxCUIs."""
        return self._search(
            "rxterms",
            arguments,
            display_fields=["DISPLAY_NAME", "STRENGTHS_AND_FORMS"],
            extra_fields=["STRENGTHS_AND_FORMS", "RXCUIS"],
        )

    def _search_conditions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Patient problem-list autocomplete with ICD-10-CM/ICD-9 crosswalk."""
        return self._search(
            "conditions",
            arguments,
            display_fields=["primary_name", "consumer_name"],
            extra_fields=["icd10cm_codes", "term_icd9_code"],
        )

    def _search_disease_names(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Disease-name autocomplete; the code field is the UMLS CUI."""
        return self._search(
            "disease_names",
            arguments,
            display_fields=["primary_name"],
            extra_fields=[],
            send_df=False,
        )

    _OPERATION_MAP = {
        "RxTerms_search": "_search_rxterms",
        "HealthConditions_search": "_search_conditions",
        "DiseaseNames_search": "_search_disease_names",
    }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = self.tool_config.get("name", "")
        for key, method_name in self._OPERATION_MAP.items():
            if key in tool_name:
                return getattr(self, method_name)(arguments)
        return {"status": "error", "error": f"Unknown operation for tool: {tool_name}"}
