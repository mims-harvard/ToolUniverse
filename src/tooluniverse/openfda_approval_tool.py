"""
OpenFDA Drug Approvals Tool - FDA Drug Approval and Registration Data

Provides access to the openFDA Drugs@FDA endpoint (drugsfda.json) which contains
FDA drug approval history, application types (NDA/ANDA/BLA), submission timelines,
sponsor/manufacturer information, approved products with dosage forms and strengths,
therapeutic equivalence codes, and marketing status.

This data is sourced from FDA's Drugs@FDA database and covers:
- New Drug Applications (NDA) - brand-name drugs
- Abbreviated New Drug Applications (ANDA) - generic drugs
- Biologic License Applications (BLA) - biologics
- Submission history (original, supplement, tentative approvals)
- Product details (active ingredients, dosage forms, routes, strengths)

API base: https://api.fda.gov/drug/drugsfda.json
No authentication required (optional API key for higher rate limits).

Reference: https://open.fda.gov/apis/drug/drugsfda/
"""

import os
import requests
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool
from .tool_registry import register_tool


FDA_DRUGSFDA_URL = "https://api.fda.gov/drug/drugsfda.json"


@register_tool("OpenFDAApprovalTool")
class OpenFDAApprovalTool(BaseTool):
    """
    Tool for querying FDA drug approval and registration data via openFDA.

    Uses the Drugs@FDA API to retrieve drug approval history, application
    types, sponsor information, and approved product details.

    Supported operations:
    - search_approvals: Search drug approvals by name, sponsor, or application number
    - get_approval_history: Get complete approval/submission history for a drug
    - get_approved_products: Get approved product details (strengths, forms, routes)
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.timeout = 30

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the OpenFDA Drug Approvals tool with given arguments."""
        operation = arguments.get("operation") or (
            self.tool_config.get("fields") or {}
        ).get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        operation_handlers = {
            "search_approvals": self._search_approvals,
            "get_approval_history": self._get_approval_history,
            "get_approved_products": self._get_approved_products,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": "Unknown operation: {}".format(operation),
                "available_operations": list(operation_handlers.keys()),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "openFDA request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to openFDA"}
        except Exception as e:
            return {
                "status": "error",
                "error": "openFDA operation failed: {}".format(str(e)),
            }

    def _make_request(
        self, search: str, limit: int = 5, offset: int = 0
    ) -> Dict[str, Any]:
        """Make GET request to openFDA drugsfda endpoint."""
        params = {"search": search, "limit": limit, "skip": offset}
        api_key = os.environ.get("FDA_API_KEY")
        if api_key:
            params["api_key"] = api_key
        response = requests.get(FDA_DRUGSFDA_URL, params=params, timeout=self.timeout)
        if response.status_code == 404:
            return {"status": "not_found", "status_code": 404}
        if response.status_code != 200:
            return {
                "status": "error",
                "status_code": response.status_code,
                "error": "openFDA Drugs@FDA returned HTTP {}".format(
                    response.status_code
                ),
                "detail": (response.text or "")[:500],
            }
        try:
            payload = response.json()
        except ValueError:
            return {
                "status": "error",
                "status_code": 200,
                "error": "openFDA Drugs@FDA returned invalid JSON",
            }
        if not isinstance(payload, dict):
            return {
                "status": "error",
                "status_code": 200,
                "error": "openFDA Drugs@FDA returned an unexpected payload",
            }
        return {"status": "success", "payload": payload}

    @staticmethod
    def _quoted(value: str) -> str:
        """Escape a value embedded in an openFDA/Lucene quoted expression."""
        return value.replace("\\", "\\\\").replace('"', '\\"')

    @staticmethod
    def _validate_optional_text(arguments: Dict[str, Any], name: str):
        value = arguments.get(name)
        if value is None:
            return None, None
        if not isinstance(value, str) or not value.strip():
            return None, {
                "status": "error",
                "error": "{} must be a non-empty string".format(name),
            }
        return value.strip(), None

    def _resolve_single_application(
        self, drug_name: Optional[str], application_number: Optional[str]
    ) -> Dict[str, Any]:
        if drug_name and application_number:
            return {
                "status": "error",
                "error": "Provide either drug_name or application_number, not both",
            }
        if application_number:
            search = 'application_number:"{}"'.format(self._quoted(application_number))
        elif drug_name:
            escaped = self._quoted(drug_name)
            search = '(openfda.brand_name:"{}" OR openfda.generic_name:"{}")'.format(
                escaped, escaped
            )
        else:
            return {
                "status": "error",
                "error": "Either drug_name or application_number is required",
            }

        requested = self._make_request(search, 100, 0)
        if requested["status"] == "error":
            return requested
        if requested["status"] == "not_found":
            return {"status": "not_found", "search": search}

        payload = requested["payload"]
        results = payload.get("results")
        meta_results = (payload.get("meta") or {}).get("results") or {}
        total = meta_results.get("total")
        if (
            not isinstance(results, list)
            or isinstance(total, bool)
            or not isinstance(total, int)
        ):
            return {
                "status": "error",
                "error": "openFDA Drugs@FDA response omitted results or exact total metadata",
            }
        if application_number and (total != 1 or len(results) != 1):
            return {
                "status": "error",
                "error": (
                    "Exact application_number query returned {} records; "
                    "cannot select a trustworthy application"
                ).format(total),
                "total_applications": total,
                "search": search,
            }
        if total != 1 or len(results) != 1:
            return {
                "status": "error",
                "error_type": "ambiguous_query",
                "error": (
                    "Drug name matched {} FDA applications; provide one exact "
                    "application_number from OpenFDA_search_drug_approvals"
                ).format(total),
                "total_applications": total,
                "candidate_application_numbers": [
                    item.get("application_number")
                    for item in results
                    if isinstance(item, dict)
                ],
                "candidate_list_complete": len(results) == total,
                "search": search,
            }
        return {
            "status": "success",
            "result": results[0],
            "search": search,
            "total_applications": total,
        }

    def _format_date(self, date_str: Optional[str]) -> Optional[str]:
        """Format YYYYMMDD date to YYYY-MM-DD."""
        if not date_str or len(date_str) < 8:
            return date_str
        return "{}-{}-{}".format(date_str[:4], date_str[4:6], date_str[6:8])

    def _extract_approval_summary(self, result: Dict) -> Dict:
        """Extract a summary from a drugsfda result."""
        openfda = result.get("openfda", {})

        # Get submission dates and sort by most recent
        submissions = result.get("submissions", [])
        sorted_subs = sorted(
            submissions,
            key=lambda s: s.get("submission_status_date", ""),
            reverse=True,
        )

        approved_originals = [
            sub
            for sub in submissions
            if sub.get("submission_type") == "ORIG"
            and sub.get("submission_status") == "AP"
        ]
        original_approval = min(
            approved_originals,
            key=lambda sub: sub.get("submission_status_date", "99999999"),
            default=None,
        )

        # Get products info
        products = result.get("products", [])
        active_ingredients = set()
        dosage_forms = set()
        routes = set()
        strengths = set()
        for prod in products:
            ai = prod.get("active_ingredients", [])
            for ing in ai:
                name = ing.get("name")
                if name:
                    active_ingredients.add(name)
                strength = ing.get("strength")
                if strength:
                    strengths.add(strength)
            df = prod.get("dosage_form")
            if df:
                dosage_forms.add(df)
            rt = prod.get("route")
            if rt:
                routes.add(rt)

        brand_names = openfda.get("brand_name", [])
        generic_names = openfda.get("generic_name", [])

        return {
            "application_number": result.get("application_number"),
            "sponsor_name": result.get("sponsor_name"),
            "brand_name": ", ".join(brand_names) if brand_names else None,
            "generic_name": ", ".join(generic_names) if generic_names else None,
            "brand_names": brand_names,
            "generic_names": generic_names,
            "active_ingredients": sorted(active_ingredients)
            if active_ingredients
            else None,
            "dosage_forms": sorted(dosage_forms) if dosage_forms else None,
            "routes": sorted(routes) if routes else None,
            "strengths": sorted(strengths) if strengths else None,
            "original_approval_date": self._format_date(
                original_approval.get("submission_status_date")
            )
            if original_approval
            else None,
            "most_recent_submission_date": self._format_date(
                sorted_subs[0].get("submission_status_date")
            )
            if sorted_subs
            else None,
            "total_submissions": len(submissions),
            "product_count": len(products),
        }

    def _search_approvals(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search drug approvals by name, sponsor, or application number."""
        drug_name, error = self._validate_optional_text(arguments, "drug_name")
        if error:
            return error
        sponsor, error = self._validate_optional_text(arguments, "sponsor")
        if error:
            return error
        application_number, error = self._validate_optional_text(
            arguments, "application_number"
        )
        if error:
            return error
        limit = arguments.get("limit", 5)
        offset = arguments.get("offset", 0)
        if limit is None:
            limit = 5
        if offset is None:
            offset = 0
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 100
        ):
            return {
                "status": "error",
                "error": "limit must be an integer from 1 to 100",
            }
        if (
            isinstance(offset, bool)
            or not isinstance(offset, int)
            or not 0 <= offset <= 26000
        ):
            return {
                "status": "error",
                "error": "offset must be an integer from 0 to 26000",
            }

        if not drug_name and not sponsor and not application_number:
            return {
                "status": "error",
                "error": "At least one of drug_name, sponsor, or application_number is required",
            }

        # Build search query
        parts = []
        if drug_name:
            escaped = self._quoted(drug_name)
            parts.append(
                '(openfda.brand_name:"{}" OR openfda.generic_name:"{}")'.format(
                    escaped, escaped
                )
            )
        if sponsor:
            parts.append('sponsor_name:"{}"'.format(self._quoted(sponsor)))
        if application_number:
            parts.append(
                'application_number:"{}"'.format(self._quoted(application_number))
            )
        search = " AND ".join(parts)

        requested = self._make_request(search, limit, offset)
        if requested["status"] == "error":
            return requested
        if requested["status"] == "not_found":
            return {
                "status": "success",
                "data": {
                    "query": search,
                    "total": 0,
                    "approvals": [],
                    "message": "No FDA drug approvals found",
                },
                "metadata": {
                    "total_matches": 0,
                    "total_matches_is_exact": True,
                    "returned": 0,
                    "limit": limit,
                    "offset": offset,
                    "has_more": False,
                    "next_offset": None,
                    "result_set_complete": offset == 0,
                },
            }

        data = requested["payload"]
        results = data.get("results")
        meta_results = (data.get("meta") or {}).get("results") or {}
        total = meta_results.get("total")
        upstream_skip = meta_results.get("skip")
        upstream_limit = meta_results.get("limit")
        if (
            not isinstance(results, list)
            or isinstance(total, bool)
            or not isinstance(total, int)
            or upstream_skip != offset
            or upstream_limit != limit
        ):
            return {
                "status": "error",
                "error": "openFDA Drugs@FDA returned invalid or conflicting pagination metadata",
            }
        approvals = [
            self._extract_approval_summary(result)
            for result in results
            if isinstance(result, dict)
        ]
        if len(approvals) != len(results):
            return {
                "status": "error",
                "error": "openFDA Drugs@FDA returned a malformed approval record",
            }
        next_offset = offset + len(approvals)
        more_results_exist = next_offset < total
        has_more = more_results_exist and next_offset <= 26000

        return {
            "status": "success",
            "data": {
                "query": search,
                "total": total,
                "approvals": approvals,
            },
            "metadata": {
                "total_matches": total,
                "total_matches_is_exact": True,
                "returned": len(approvals),
                "limit": limit,
                "offset": offset,
                "more_results_exist": more_results_exist,
                "has_more": has_more,
                "next_offset": next_offset if has_more else None,
                "upstream_window_exhausted": more_results_exist and not has_more,
                "result_set_complete": offset == 0 and not more_results_exist,
            },
        }

    def _get_approval_history(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get complete approval/submission history for a drug."""
        drug_name, error = self._validate_optional_text(arguments, "drug_name")
        if error:
            return error
        application_number, error = self._validate_optional_text(
            arguments, "application_number"
        )
        if error:
            return error
        resolved = self._resolve_single_application(drug_name, application_number)
        if resolved["status"] == "not_found":
            return {
                "status": "error",
                "error": "Drug not found in FDA approvals database",
            }
        if resolved["status"] == "error":
            return resolved

        result = resolved["result"]
        openfda = result.get("openfda", {})
        submissions = result.get("submissions", [])

        # Sort submissions chronologically
        sorted_subs = sorted(
            submissions,
            key=lambda s: s.get("submission_status_date", ""),
        )

        history = []
        for sub in sorted_subs:
            entry = {
                "submission_type": sub.get("submission_type"),
                "submission_number": sub.get("submission_number"),
                "submission_status": sub.get("submission_status"),
                "submission_status_date": self._format_date(
                    sub.get("submission_status_date")
                ),
                "review_priority": sub.get("review_priority"),
                "submission_class_code": sub.get("submission_class_code"),
                "submission_class_description": sub.get(
                    "submission_class_code_description"
                ),
            }
            # Include application docs if present
            app_docs = sub.get("application_docs", [])
            if app_docs:
                entry["application_docs"] = [
                    {
                        "id": doc.get("id"),
                        "type": doc.get("type"),
                        "title": doc.get("title"),
                        "url": doc.get("url"),
                    }
                    for doc in app_docs
                ]
            history.append(entry)

        brand_names = openfda.get("brand_name", [])
        generic_names = openfda.get("generic_name", [])

        return {
            "status": "success",
            "data": {
                "application_number": result.get("application_number"),
                "sponsor_name": result.get("sponsor_name"),
                "brand_name": ", ".join(brand_names) if brand_names else None,
                "generic_name": ", ".join(generic_names) if generic_names else None,
                "brand_names": brand_names,
                "generic_names": generic_names,
                "total_submissions": len(history),
                "submission_history": history,
            },
            "metadata": {
                "application_selection": "exact_unique_match",
                "matched_applications": 1,
                "search": resolved["search"],
                "all_submission_documents_included": True,
                "result_set_complete": True,
            },
        }

    def _get_approved_products(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get approved product details for a drug."""
        drug_name, error = self._validate_optional_text(arguments, "drug_name")
        if error:
            return error
        application_number, error = self._validate_optional_text(
            arguments, "application_number"
        )
        if error:
            return error
        resolved = self._resolve_single_application(drug_name, application_number)
        if resolved["status"] == "not_found":
            return {
                "status": "error",
                "error": "Drug not found in FDA approvals database",
            }
        if resolved["status"] == "error":
            return resolved

        result = resolved["result"]
        openfda = result.get("openfda", {})
        products = result.get("products", [])

        formatted_products = []
        for prod in products:
            active_ingredients = []
            for ai in prod.get("active_ingredients", []):
                active_ingredients.append(
                    {
                        "name": ai.get("name"),
                        "strength": ai.get("strength"),
                    }
                )

            formatted_products.append(
                {
                    "product_number": prod.get("product_number"),
                    "brand_name": prod.get("brand_name"),
                    "active_ingredients": active_ingredients,
                    "dosage_form": prod.get("dosage_form"),
                    "route": prod.get("route"),
                    "marketing_status": prod.get("marketing_status"),
                    "reference_drug": prod.get("reference_drug"),
                    "te_code": prod.get("te_code"),
                }
            )

        brand_names = openfda.get("brand_name", [])
        generic_names = openfda.get("generic_name", [])

        return {
            "status": "success",
            "data": {
                "application_number": result.get("application_number"),
                "sponsor_name": result.get("sponsor_name"),
                "brand_name": ", ".join(brand_names) if brand_names else None,
                "generic_name": ", ".join(generic_names) if generic_names else None,
                "brand_names": brand_names,
                "generic_names": generic_names,
                "total_products": len(formatted_products),
                "products": formatted_products,
            },
            "metadata": {
                "application_selection": "exact_unique_match",
                "matched_applications": 1,
                "search": resolved["search"],
                "result_set_complete": True,
            },
        }
