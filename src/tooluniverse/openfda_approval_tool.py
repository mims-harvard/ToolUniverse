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
        operation = arguments.get("operation")
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

    def _make_request(self, search: str, limit: int = 5) -> Optional[Dict[str, Any]]:
        """Make GET request to openFDA drugsfda endpoint."""
        params = {"search": search, "limit": min(limit, 100)}
        response = requests.get(FDA_DRUGSFDA_URL, params=params, timeout=self.timeout)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            return None

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

        # Find original approval
        original_approval = None
        for sub in submissions:
            if (
                sub.get("submission_type") == "ORIG"
                and sub.get("submission_status") == "AP"
            ):
                original_approval = sub
                break

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
            "brand_name": ", ".join(brand_names[:3]) if brand_names else None,
            "generic_name": ", ".join(generic_names[:3]) if generic_names else None,
            "active_ingredients": sorted(active_ingredients)
            if active_ingredients
            else None,
            "dosage_forms": sorted(dosage_forms) if dosage_forms else None,
            "routes": sorted(routes) if routes else None,
            "strengths": sorted(strengths)[:5] if strengths else None,
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
        drug_name = arguments.get("drug_name")
        sponsor = arguments.get("sponsor")
        application_number = arguments.get("application_number")
        limit = arguments.get("limit", 5)

        if not drug_name and not sponsor and not application_number:
            return {
                "status": "error",
                "error": "At least one of drug_name, sponsor, or application_number is required",
            }

        # Build search query
        parts = []
        if drug_name:
            parts.append(
                '(openfda.brand_name:"{}" OR openfda.generic_name:"{}")'.format(
                    drug_name, drug_name
                )
            )
        if sponsor:
            parts.append('sponsor_name:"{}"'.format(sponsor))
        if application_number:
            parts.append('application_number:"{}"'.format(application_number))
        search = " AND ".join(parts)

        data = self._make_request(search, limit)
        if not data or "results" not in data:
            return {
                "status": "success",
                "data": {
                    "query": search,
                    "total": 0,
                    "approvals": [],
                    "message": "No FDA drug approvals found",
                },
            }

        total = data.get("meta", {}).get("results", {}).get("total", 0)
        approvals = [self._extract_approval_summary(r) for r in data["results"]]

        return {
            "status": "success",
            "data": {
                "query": search,
                "total": total,
                "approvals": approvals,
            },
        }

    def _get_approval_history(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get complete approval/submission history for a drug."""
        drug_name = arguments.get("drug_name")
        application_number = arguments.get("application_number")

        if not drug_name and not application_number:
            return {
                "status": "error",
                "error": "Either drug_name or application_number is required",
            }

        if application_number:
            search = 'application_number:"{}"'.format(application_number)
        else:
            search = '(openfda.brand_name:"{}" OR openfda.generic_name:"{}")'.format(
                drug_name, drug_name
            )

        data = self._make_request(search, 1)
        if not data or "results" not in data:
            return {
                "status": "error",
                "error": "Drug not found in FDA approvals database",
            }

        result = data["results"][0]
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
                    for doc in app_docs[:5]
                ]
            history.append(entry)

        brand_names = openfda.get("brand_name", [])
        generic_names = openfda.get("generic_name", [])

        return {
            "status": "success",
            "data": {
                "application_number": result.get("application_number"),
                "sponsor_name": result.get("sponsor_name"),
                "brand_name": ", ".join(brand_names[:3]) if brand_names else None,
                "generic_name": ", ".join(generic_names[:3]) if generic_names else None,
                "total_submissions": len(history),
                "submission_history": history,
            },
        }

    def _get_approved_products(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get approved product details for a drug."""
        drug_name = arguments.get("drug_name")
        application_number = arguments.get("application_number")

        if not drug_name and not application_number:
            return {
                "status": "error",
                "error": "Either drug_name or application_number is required",
            }

        if application_number:
            search = 'application_number:"{}"'.format(application_number)
        else:
            search = '(openfda.brand_name:"{}" OR openfda.generic_name:"{}")'.format(
                drug_name, drug_name
            )

        data = self._make_request(search, 1)
        if not data or "results" not in data:
            return {
                "status": "error",
                "error": "Drug not found in FDA approvals database",
            }

        result = data["results"][0]
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
                "brand_name": ", ".join(brand_names[:3]) if brand_names else None,
                "generic_name": ", ".join(generic_names[:3]) if generic_names else None,
                "total_products": len(formatted_products),
                "products": formatted_products,
            },
        }
