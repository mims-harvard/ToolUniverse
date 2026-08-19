# openfda_device_tool.py
"""
openFDA medical device tool for ToolUniverse.

ToolUniverse's existing openFDA tools cover only the drug endpoints
(drug/event, drug/label, drug/drugsfda); the device side -- device
recalls and MAUDE (Manufacturer and User Facility Device Experience)
adverse event reports -- had no coverage at all. These are a genuinely
different record schema (device brand/generic name, recall
classification and root cause, patient problem codes) from the
drug-adverse-event tools, not a parameter variation of them.

A bare `search=<term>` full-text query was verified to discriminate
correctly (a nonsense term returns a clean 404 "no matches", not an
inflated count) before building this, given this exact codebase's own
git history documents prior openFDA quoting/exactness bugs.

API: https://api.fda.gov/device
No authentication required (optional api_key raises the rate limit).
"""

from typing import Any, Dict, List

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

RECALL_URL = "https://api.fda.gov/device/recall.json"
EVENT_URL = "https://api.fda.gov/device/event.json"


@register_tool("OpenFDADeviceTool")
class OpenFDADeviceTool(BaseTool):
    """
    Tool for querying openFDA's medical device recall and adverse event
    (MAUDE) data.

    Supports searching device recalls (reason, root cause, recalling
    firm) and MAUDE adverse event reports (device, event type, patient
    problems) by device name.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_recalls"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the openFDA device lookup."""
        try:
            if self.operation == "search_recalls":
                return self._search_recalls(arguments)
            if self.operation == "search_adverse_events":
                return self._search_adverse_events(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"openFDA request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to openFDA. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"openFDA returned HTTP {code}"}
        except ValueError:
            return {"status": "error", "error": "openFDA returned a non-JSON response"}
        except Exception as e:
            return {"status": "error", "error": f"Error querying openFDA: {str(e)}"}

    def _search_recalls(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search medical device recalls by device name or free text."""
        query = (arguments.get("query") or "").strip()
        if not query:
            return {
                "status": "error",
                "error": "query is required, e.g. 'pacemaker' or a "
                "recalling firm name.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 20
        limit = min(limit, 100)

        response = requests.get(
            RECALL_URL, params={"search": query, "limit": limit}, timeout=self.timeout
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No device recalls matching '{query}'.",
            }
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []

        rows = [
            {
                "product_description": r.get("product_description"),
                "recalling_firm": r.get("recalling_firm"),
                "reason_for_recall": r.get("reason_for_recall"),
                "root_cause_description": r.get("root_cause_description"),
                "recall_status": r.get("recall_status"),
                "event_date_initiated": r.get("event_date_initiated"),
                "action": r.get("action"),
            }
            for r in results
        ]

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "query": query,
                "total_matching": (payload.get("meta") or {})
                .get("results", {})
                .get("total"),
                "returned": len(rows),
                "source": "openFDA device/recall",
            },
        }

    def _search_adverse_events(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search MAUDE device adverse event reports by device name."""
        device_name = (arguments.get("device_name") or "").strip()
        if not device_name:
            return {
                "status": "error",
                "error": "device_name is required, e.g. 'pacemaker' or "
                "'insulin pump'.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 20
        limit = min(limit, 100)

        response = requests.get(
            EVENT_URL,
            params={
                "search": f"device.generic_name:{device_name}",
                "limit": limit,
            },
            timeout=self.timeout,
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No MAUDE adverse event reports for device "
                f"'{device_name}'.",
            }
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []

        rows: List[Dict[str, Any]] = []
        for r in results:
            devices = r.get("device") or [{}]
            device = devices[0] if devices else {}
            patients = r.get("patient") or []
            patient_problems: List[str] = []
            for p in patients:
                patient_problems.extend(p.get("patient_problems") or [])
            rows.append(
                {
                    "brand_name": device.get("brand_name"),
                    "generic_name": device.get("generic_name"),
                    "manufacturer": device.get("manufacturer_d_name"),
                    "event_type": r.get("event_type"),
                    "date_of_event": r.get("date_of_event"),
                    "product_problems": r.get("product_problems") or [],
                    "patient_problems": sorted(set(patient_problems)),
                }
            )

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "device_name": device_name,
                "total_matching": (payload.get("meta") or {})
                .get("results", {})
                .get("total"),
                "returned": len(rows),
                "source": "openFDA device/event (MAUDE)",
            },
        }
