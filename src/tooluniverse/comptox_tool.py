"""
EPA CompTox / CCTE API Tool

Provides programmatic access to the US EPA's Computational Toxicology and
Exposure (CTX) APIs, the backend behind the CompTox Chemicals Dashboard
(https://comptox.epa.gov/dashboard/). Covers three microservices:

- Chemical: chemical identity search and structural/property detail
- Hazard: curated human and eco-toxicity hazard values (ToxVal)
- Bioactivity: quantitative high-throughput screening results from
  ToxCast/Tox21 (dose-response hit calls across ~700+ assays)

API docs: https://comptox.epa.gov/ctx-api/docs/chemical.html (and
hazard.html, bioactivity.html). OpenAPI specs at
https://comptox.epa.gov/ctx-api/docs/{chemical,hazard,bioactivity}.json.
Authentication: API key via the "x-api-key" HTTP header. Free; obtained by
emailing ccte_api@epa.gov.
"""

import os
import requests
from typing import Any, Dict, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

_API_KEY_FROM_ENV = object()

BASE_URL = "https://comptox.epa.gov/ctx-api"


@register_tool("CompToxTool")
class CompToxTool(BaseTool):
    """
    Tool for querying EPA's CompTox/CCTE Chemical, Hazard, and
    Bioactivity APIs.

    Requires an API key via the EPA_COMPTOX_API_KEY environment variable,
    sent as the "x-api-key" header. Free; request one by emailing
    ccte_api@epa.gov.
    """

    def __init__(
        self,
        tool_config: Dict[str, Any],
        api_key: Optional[str] = _API_KEY_FROM_ENV,
        timeout: int = 30,
    ):
        super().__init__(tool_config)
        self.timeout = timeout
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        if api_key is _API_KEY_FROM_ENV:
            api_key = os.environ.get("EPA_COMPTOX_API_KEY")
        self.api_key = api_key

    def _headers(self) -> Dict[str, str]:
        return {"Accept": "application/json", "x-api-key": self.api_key}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation")
        if not operation:
            return {
                "status": "error",
                "error": "Missing required parameter: operation",
            }

        if not self.api_key:
            return {
                "status": "error",
                "error": (
                    "EPA CompTox API key required. Set EPA_COMPTOX_API_KEY "
                    "to a valid key. Request one (free) by emailing "
                    "ccte_api@epa.gov."
                ),
            }

        handlers = {
            "search_chemical": self._search_chemical,
            "get_chemical_detail": self._get_chemical_detail,
            "get_hazard_data": self._get_hazard_data,
            "get_bioactivity_summary": self._get_bioactivity_summary,
            "get_bioactivity_assays": self._get_bioactivity_assays,
        }

        handler = handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": "Unknown operation: {}. Available: {}".format(
                    operation, ", ".join(handlers.keys())
                ),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "CompTox API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to CompTox API"}
        except Exception as e:  # noqa: BLE001 - surfaced to the caller, not raised
            return {"status": "error", "error": "Operation failed: {}".format(str(e))}

    @staticmethod
    def _auth_error(response) -> Optional[Dict[str, Any]]:
        if response.status_code in (401, 403):
            return {
                "status": "error",
                "error": (
                    "Authentication failed (HTTP {}). Check that "
                    "EPA_COMPTOX_API_KEY holds a current, valid key."
                ).format(response.status_code),
            }
        if response.status_code == 404:
            return {
                "status": "error",
                "error": "No CompTox record found for this identifier.",
            }
        return None

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None):
        return requests.get(
            BASE_URL + path,
            params=params or {},
            headers=self._headers(),
            timeout=self.timeout,
        )

    def _search_chemical(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve a chemical name, CASRN, DTXSID, DTXCID, or InChIKey to identity records."""
        word = arguments.get("word")
        if not word:
            return {"status": "error", "error": "Missing required parameter: word"}

        match_type = arguments.get("match_type") or "equal"
        if match_type not in ("equal", "start-with", "contain"):
            return {
                "status": "error",
                "error": "match_type must be one of: equal, start-with, contain",
            }

        response = self._get("/chemical/search/{}/{}".format(match_type, word))

        auth_err = self._auth_error(response)
        if auth_err:
            return auth_err

        response.raise_for_status()
        results = response.json()
        if not isinstance(results, list):
            results = [results] if results else []

        return {
            "status": "success",
            "data": {"results": results, "result_count": len(results)},
            "metadata": {
                "source": "EPA CompTox",
                "word": word,
                "match_type": match_type,
            },
        }

    def _get_chemical_detail(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get full chemical structure/property detail by DTXSID."""
        dtxsid = arguments.get("dtxsid")
        if not dtxsid:
            return {"status": "error", "error": "Missing required parameter: dtxsid"}

        params = {"projection": arguments.get("projection") or "chemicaldetailall"}
        response = self._get(
            "/chemical/detail/search/by-dtxsid/{}".format(dtxsid), params=params
        )

        auth_err = self._auth_error(response)
        if auth_err:
            return auth_err

        response.raise_for_status()
        detail = response.json()

        return {
            "status": "success",
            "data": detail,
            "metadata": {"source": "EPA CompTox", "dtxsid": dtxsid},
        }

    def _get_hazard_data(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get curated hazard/toxicity values (ToxVal) for a chemical by DTXSID."""
        dtxsid = arguments.get("dtxsid")
        if not dtxsid:
            return {"status": "error", "error": "Missing required parameter: dtxsid"}

        response = self._get("/hazard/toxval/search/by-dtxsid/{}".format(dtxsid))

        auth_err = self._auth_error(response)
        if auth_err:
            return auth_err

        response.raise_for_status()
        records = response.json()
        if not isinstance(records, list):
            records = [records] if records else []

        return {
            "status": "success",
            "data": {"toxval_records": records, "record_count": len(records)},
            "metadata": {"source": "EPA CompTox Hazard (ToxVal)", "dtxsid": dtxsid},
        }

    def _get_bioactivity_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get aggregate ToxCast/Tox21 high-throughput screening summary for a chemical by DTXSID."""
        dtxsid = arguments.get("dtxsid")
        if not dtxsid:
            return {"status": "error", "error": "Missing required parameter: dtxsid"}

        response = self._get(
            "/bioactivity/data/summary/search/by-dtxsid/{}".format(dtxsid)
        )

        auth_err = self._auth_error(response)
        if auth_err:
            return auth_err

        response.raise_for_status()
        summary = response.json()

        return {
            "status": "success",
            "data": summary,
            "metadata": {"source": "EPA CompTox Bioactivity (ToxCast/Tox21)", "dtxsid": dtxsid},
        }

    def _get_bioactivity_assays(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get per-assay ToxCast/Tox21 dose-response hit-call records for a chemical by DTXSID."""
        dtxsid = arguments.get("dtxsid")
        if not dtxsid:
            return {"status": "error", "error": "Missing required parameter: dtxsid"}

        response = self._get("/bioactivity/data/search/by-dtxsid/{}".format(dtxsid))

        auth_err = self._auth_error(response)
        if auth_err:
            return auth_err

        response.raise_for_status()
        records = response.json()
        if not isinstance(records, list):
            records = [records] if records else []

        return {
            "status": "success",
            "data": {"assay_records": records, "record_count": len(records)},
            "metadata": {"source": "EPA CompTox Bioactivity (ToxCast/Tox21)", "dtxsid": dtxsid},
        }
