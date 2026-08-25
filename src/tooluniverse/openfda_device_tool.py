# openfda_device_tool.py
"""
openFDA medical device tool for ToolUniverse.

ToolUniverse's existing openFDA tools cover only the drug endpoints
(drug/event, drug/label, drug/drugsfda); the device side had no coverage
at all. Covers recalls, MAUDE (Manufacturer and User Facility Device
Experience) adverse event reports, the UDI (Unique Device Identifier)
database, regulatory classification, and both premarket pathways --
510(k) notification and PMA (premarket approval) for higher-risk
devices. These are a genuinely different record schema (device brand/
generic name, recall classification and root cause, patient problem
codes, regulatory clearance numbers) from the drug-adverse-event tools,
not a parameter variation of them.

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
UDI_URL = "https://api.fda.gov/device/udi.json"
CLASSIFICATION_URL = "https://api.fda.gov/device/classification.json"
K510_URL = "https://api.fda.gov/device/510k.json"
PMA_URL = "https://api.fda.gov/device/pma.json"


@register_tool("OpenFDADeviceTool")
class OpenFDADeviceTool(BaseTool):
    """
    Tool for querying openFDA's medical device recall and adverse event
    (MAUDE) data.

    Supports searching device recalls (reason, root cause, recalling
    firm), MAUDE adverse event reports (device, event type, patient
    problems), the UDI database, regulatory classification, and 510(k)/
    PMA premarket clearances, all by device name.

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
            if self.operation == "search_udi":
                return self._search_udi(arguments)
            if self.operation == "get_classification":
                return self._get_classification(arguments)
            if self.operation == "search_510k":
                return self._search_510k(arguments)
            if self.operation == "search_pma":
                return self._search_pma(arguments)
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

    def _search_udi(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search the Unique Device Identifier (UDI) database."""
        query = (arguments.get("query") or "").strip()
        if not query:
            return {
                "status": "error",
                "error": "query is required, e.g. 'pacemaker' or a "
                "company name.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 20
        limit = min(limit, 100)

        response = requests.get(
            UDI_URL, params={"search": query, "limit": limit}, timeout=self.timeout
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No UDI records matching '{query}'.",
            }
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []

        rows = []
        for r in results:
            product_codes = r.get("product_codes") or [{}]
            first_code = product_codes[0] if product_codes else {}
            identifiers = r.get("identifiers") or []
            gmdn_terms = r.get("gmdn_terms") or []
            rows.append(
                {
                    "brand_name": r.get("brand_name"),
                    "company_name": r.get("company_name"),
                    "device_description": r.get("device_description"),
                    "primary_di": next(
                        (
                            i.get("id")
                            for i in identifiers
                            if i.get("type") == "Primary"
                        ),
                        None,
                    ),
                    "gmdn_terms": [g.get("name") for g in gmdn_terms if g.get("name")],
                    "device_class": (first_code.get("openfda") or {}).get(
                        "device_class"
                    ),
                    "commercial_distribution_status": r.get(
                        "commercial_distribution_status"
                    ),
                }
            )

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "query": query,
                "total_matching": (payload.get("meta") or {})
                .get("results", {})
                .get("total"),
                "returned": len(rows),
                "source": "openFDA device/udi",
            },
        }

    def _get_classification(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search device regulatory classification by device name."""
        device_name = (arguments.get("device_name") or "").strip()
        if not device_name:
            return {
                "status": "error",
                "error": "device_name is required, e.g. 'pacemaker'.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 20
        limit = min(limit, 100)

        response = requests.get(
            CLASSIFICATION_URL,
            params={"search": f"device_name:{device_name}", "limit": limit},
            timeout=self.timeout,
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No device classification found for "
                f"'{device_name}'.",
            }
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []

        rows = [
            {
                "device_name": r.get("device_name"),
                "product_code": r.get("product_code"),
                "device_class": r.get("device_class"),
                "review_panel": r.get("review_panel"),
                "medical_specialty_description": r.get(
                    "medical_specialty_description"
                ),
                "regulation_number": r.get("regulation_number"),
                "third_party_flag": r.get("third_party_flag"),
            }
            for r in results
        ]

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "device_name": device_name,
                "total_matching": (payload.get("meta") or {})
                .get("results", {})
                .get("total"),
                "returned": len(rows),
                "note": "device_class: 1 = general controls, 2 = special "
                "controls, 3 = premarket approval.",
                "source": "openFDA device/classification",
            },
        }

    def _search_510k(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search 510(k) premarket notification clearances."""
        device_name = (arguments.get("device_name") or "").strip()
        if not device_name:
            return {
                "status": "error",
                "error": "device_name is required, e.g. 'pacemaker'.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 20
        limit = min(limit, 100)

        response = requests.get(
            K510_URL,
            params={"search": f"device_name:{device_name}", "limit": limit},
            timeout=self.timeout,
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No 510(k) clearances found for '{device_name}'.",
            }
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []

        rows = [
            {
                "k_number": r.get("k_number"),
                "device_name": r.get("device_name"),
                "applicant": r.get("applicant"),
                "decision_date": r.get("decision_date"),
                "decision_description": r.get("decision_description"),
                "clearance_type": r.get("clearance_type"),
                "advisory_committee_description": r.get(
                    "advisory_committee_description"
                ),
            }
            for r in results
        ]

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "device_name": device_name,
                "total_matching": (payload.get("meta") or {})
                .get("results", {})
                .get("total"),
                "returned": len(rows),
                "source": "openFDA device/510k",
            },
        }

    def _search_pma(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search premarket approval (PMA) applications for high-risk devices."""
        device_name = (arguments.get("device_name") or "").strip()
        if not device_name:
            return {
                "status": "error",
                "error": "device_name is required, e.g. 'defibrillator'.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 20
        limit = min(limit, 100)

        response = requests.get(
            PMA_URL,
            params={"search": f"trade_name:{device_name}", "limit": limit},
            timeout=self.timeout,
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No PMA applications found for '{device_name}'.",
            }
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []

        rows = [
            {
                "pma_number": r.get("pma_number"),
                "trade_name": r.get("trade_name"),
                "applicant": r.get("applicant"),
                "decision_date": r.get("decision_date"),
                "ao_statement": r.get("ao_statement"),
                "advisory_committee_description": r.get(
                    "advisory_committee_description"
                ),
            }
            for r in results
        ]

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "device_name": device_name,
                "total_matching": (payload.get("meta") or {})
                .get("results", {})
                .get("total"),
                "returned": len(rows),
                "note": "ao_statement summarizes the specific approval "
                "order/change, not the whole device history.",
                "source": "openFDA device/pma",
            },
        }
