# cms_open_payments_tool.py
"""
CMS Open Payments tool for ToolUniverse.

Open Payments is the "Sunshine Act" database of payments and transfers of
value from drug and device manufacturers to US physicians and teaching
hospitals: consulting fees, meals, travel, research support, and
ownership interests, itemized by recipient, company, and associated
product. ToolUniverse had no health-economics / conflict-of-interest layer
at all.

The dataset is row-level (tens of millions of records across 2019-2025)
behind a DKAN datastore query API. Only a few columns are indexed
(covered_recipient_npi; applicable_manufacturer_or_applicable_gpo_making_
payment_id; record_id): filtering on those returns in 1-3 seconds, but an
equivalent exact-match filter on an unindexed text column like a
recipient's last name or a manufacturer's name takes roughly 25 seconds,
confirmed by direct measurement, and a LIKE/partial-match query on those
same columns exceeded a 60-second timeout entirely. Only exact-match
lookups are exposed here, and name-based lookups are documented as slow.

API: https://openpaymentsdata.cms.gov/api/1
No authentication required.
"""

from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

DATASTORE_URL = "https://openpaymentsdata.cms.gov/api/1/datastore/query"

# General Payment Data dataset identifiers, one per program year.
_YEAR_DATASETS = {
    2019: "4e54dd6c-30f8-4f86-86a7-3c109a89528e",
    2020: "a08c4b30-5cf3-4948-ad40-36f404619019",
    2021: "0380bbeb-aea1-58b6-b708-829f92a48202",
    2022: "df01c2f8-dc1f-4e79-96cb-8208beaf143c",
    2023: "fb3a65aa-c901-4a38-a813-b04b00dfa2a9",
    2024: "e6b17c6a-2534-4207-a4a1-6746a14911ff",
    2025: "fb0b1734-1410-429d-92f6-3f4b35218e5e",
}
_DEFAULT_YEAR = 2024


def _summarize(row: Dict[str, Any]) -> Dict[str, Any]:
    """Condense one Open Payments record to its scientifically useful fields."""
    return {
        "record_id": row.get("record_id"),
        "recipient_name": " ".join(
            p
            for p in (
                row.get("covered_recipient_first_name"),
                row.get("covered_recipient_last_name"),
            )
            if p
        )
        or row.get("teaching_hospital_name"),
        "recipient_npi": row.get("covered_recipient_npi") or None,
        "recipient_type": row.get("covered_recipient_type"),
        "recipient_specialty": row.get("covered_recipient_specialty_1") or None,
        "recipient_state": row.get("recipient_state"),
        "manufacturer_name": row.get(
            "applicable_manufacturer_or_applicable_gpo_making_payment_name"
        ),
        "manufacturer_id": row.get(
            "applicable_manufacturer_or_applicable_gpo_making_payment_id"
        ),
        "total_amount_usd": row.get("total_amount_of_payment_usdollars"),
        "date_of_payment": row.get("date_of_payment"),
        "nature_of_payment": row.get("nature_of_payment_or_transfer_of_value"),
        "associated_product": row.get(
            "name_of_drug_or_biological_or_device_or_medical_supply_1"
        )
        or None,
        "program_year": row.get("program_year"),
    }


@register_tool("CMSOpenPaymentsTool")
class CMSOpenPaymentsTool(BaseTool):
    """
    Tool for querying CMS Open Payments, the "Sunshine Act" database of
    payments from drug/device manufacturers to physicians and teaching
    hospitals.

    Supports exact-match lookup by recipient NPI or name, or by
    manufacturer id or name, for one program year.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_payments"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Open Payments lookup."""
        try:
            if self.operation == "search_payments":
                return self._search_payments(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Open Payments request timed out after "
                f"{self.timeout}s. Exact NPI or manufacturer_id lookups are "
                "fast; name-based lookups can take ~25s.",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to CMS Open Payments. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {
                "status": "error",
                "error": f"Open Payments returned HTTP {code}",
            }
        except ValueError:
            return {
                "status": "error",
                "error": "Open Payments returned a non-JSON response",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error querying Open Payments: {str(e)}",
            }

    def _search_payments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search one program year's payments by recipient or manufacturer."""
        npi = (arguments.get("npi") or "").strip()
        recipient_last_name = (arguments.get("recipient_last_name") or "").strip()
        manufacturer_id = (arguments.get("manufacturer_id") or "").strip()
        manufacturer_name = (arguments.get("manufacturer_name") or "").strip()

        if not any((npi, recipient_last_name, manufacturer_id, manufacturer_name)):
            return {
                "status": "error",
                "error": "Provide one of: npi, recipient_last_name, "
                "manufacturer_id, or manufacturer_name. npi and "
                "manufacturer_id are exact, indexed, and fast; the name "
                "fields are exact-match only and take roughly 25s.",
            }

        year = arguments.get("program_year")
        if not isinstance(year, int) or year not in _YEAR_DATASETS:
            year = _DEFAULT_YEAR
        dataset_id = _YEAR_DATASETS[year]

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 25
        limit = min(limit, 100)

        if npi:
            field, value = "covered_recipient_npi", npi
        elif manufacturer_id:
            field, value = (
                "applicable_manufacturer_or_applicable_gpo_making_payment_id",
                manufacturer_id,
            )
        elif recipient_last_name:
            field, value = "covered_recipient_last_name", recipient_last_name
        else:
            field, value = (
                "applicable_manufacturer_or_applicable_gpo_making_payment_name",
                manufacturer_name,
            )

        params = {
            "conditions[0][property]": field,
            "conditions[0][value]": value,
            "conditions[0][operator]": "=",
            "limit": limit,
        }
        response = requests.get(
            f"{DATASTORE_URL}/{dataset_id}/0", params=params, timeout=self.timeout
        )
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []

        if not results:
            return {
                "status": "error",
                "error": f"No Open Payments records for {field}='{value}' in "
                f"program year {year}.",
            }

        rows = [_summarize(r) for r in results]

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "program_year": year,
                "matched_field": field,
                "matched_value": value,
                "total_matching": payload.get("count"),
                "returned": len(rows),
                "note": "Amounts are per individual payment record, not "
                "aggregated across a recipient's or manufacturer's total.",
                "source": "CMS Open Payments",
            },
        }
