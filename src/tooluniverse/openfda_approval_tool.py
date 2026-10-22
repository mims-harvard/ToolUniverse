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
import re
import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool


FDA_DRUGSFDA_URL = "https://api.fda.gov/drug/drugsfda.json"

# Leading number of a strength string: "9.6MG/3ML (3.2MG/ML)" -> 9.6
_LEADING_DOSE = re.compile(r"\s*([0-9]*\.?[0-9]+)")


# Every field Drugs@FDA indexes for a drug name, in one place.
#
# This tool used to search only `(openfda.brand_name OR openfda.generic_name)`.
# The `openfda` block is *derived* -- FDA populates it by resolving an
# application to a Structured Product Label -- so when that resolution fails the
# block comes back EMPTY and the application becomes invisible by name while its
# authoritative `products.brand_name` is populated and perfectly searchable.
# Measured against the live API:
#
#   openfda.brand_name:"WEGOVY"                   -> total 0
#   products.brand_name:"WEGOVY"                  -> total 2  (NDA215256, NDA218316)
#   openfda.brand_name:"OZEMPIC"                  -> total 1  (NDA213051, oral)
#   products.brand_name:"OZEMPIC"                 -> total 2  (NDA213051 + NDA209637)
#   openfda.substance_name:"SEMAGLUTIDE"          -> total 1
#   products.active_ingredients.name:"SEMAGLUTIDE"-> total 6
#
# NDA215256 (Wegovy) and NDA209637 (Ozempic injection) both have `"openfda": {}`
# upstream. The old two-field query therefore did not merely miss Wegovy -- for
# `drug_name="Ozempic"` it returned exactly one application, NDA213051, whose
# original_approval_date is 2019-09-20 (the oral tablet), while the Ozempic
# *injection* the caller meant was approved 2017-12-05. A silent miss presented
# as a confident hit with a wrong approval date.
#
# This is the same defect shape as FAERS_DRUG_NAME_FIELDS in
# `openfda_adv_tool.py`: query only the resolved `openfda.*` name fields and
# anything openFDA failed to resolve to an SPL silently looks absent. Every
# drug-name lookup in this module must resolve to exactly this list; add a field
# only after confirming against the live API that it is indexed, and never drop
# the `products.*` entries -- they are the authoritative per-product names and
# the reason Wegovy is findable at all.
DRUGSFDA_DRUG_NAME_FIELDS = [
    "openfda.brand_name",
    "openfda.generic_name",
    "openfda.substance_name",
    "products.brand_name",
    "products.active_ingredients.name",
]


def build_drug_name_query(drug_name: str) -> str:
    """Parenthesized OR over every indexed Drugs@FDA name field.

    The parentheses are load-bearing: this group is joined to sponsor /
    application_number filters with ``AND``, and an unparenthesized OR chain
    would bind the trailing ``AND`` to the last OR branch only.
    """
    return "({})".format(
        " OR ".join(
            '{}:"{}"'.format(field, drug_name) for field in DRUGSFDA_DRUG_NAME_FIELDS
        )
    )


def _strength_sort_key(strength: str):
    """Sort strengths by their leading dose, not lexicographically.

    Plain ``sorted()`` compares these as strings, so "10MG" sorts before "2MG"
    and, for NDA215256, "7.2MG/0.75ML" and "9.6MG/3ML (3.2MG/ML)" -- the two
    highest Wegovy doses -- land at the end of the alphabetical order where the
    old ``[:5]`` cut silently dropped them. Ordering by the leading number is
    what a reader assumes a dose list means. Strengths with no leading number
    sort last, alphabetically, keeping the order total and stable.
    """
    match = _LEADING_DOSE.match(strength)
    if match:
        return (0, float(match.group(1)), strength)
    return (1, 0.0, strength)


def collect_name_lists(result: Dict):
    """Every brand and generic name for an application, as sorted lists.

    See `collect_names` for why the per-product fields are included.
    """
    openfda = result.get("openfda", {})
    brands = set(openfda.get("brand_name") or [])
    generics = set(openfda.get("generic_name") or [])
    for prod in result.get("products", []):
        if prod.get("brand_name"):
            brands.add(prod["brand_name"])
        for ing in prod.get("active_ingredients", []):
            if ing.get("name"):
                generics.add(ing["name"])
    return sorted(brands), sorted(generics)


def collect_names(result: Dict):
    """Brand and generic names for an application, as ``(brand, generic)``.

    Both are the union of the *resolved* `openfda` block and the authoritative
    per-product fields, because `openfda` is empty for NDA215256 (Wegovy) and
    NDA209637 (Ozempic injection) -- reading it alone reported
    ``brand_name: null`` for records whose products are plainly named WEGOVY /
    WEGOVY FLEXTOUCH / WEGOVY HD. Every name is returned; the previous ``[:3]``
    cuts bought nothing on lists this size while hiding real presentations.
    """
    brands, generics = collect_name_lists(result)
    return (
        ", ".join(brands) if brands else None,
        ", ".join(generics) if generics else None,
    )


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
        api_key = self.credential("FDA_API_KEY")
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

    def _format_date(self, date_str: Optional[str]) -> Optional[str]:
        """Format YYYYMMDD date to YYYY-MM-DD."""
        if not date_str or len(date_str) < 8:
            return date_str
        return "{}-{}-{}".format(date_str[:4], date_str[4:6], date_str[6:8])

    # `get_approval_history` and `get_approved_products` describe exactly one
    # application, but one drug name routinely maps to several: "Ozempic" is
    # both NDA209637 (injection, approved 2017-12-05) and NDA213051 (oral
    # tablet, approved 2019-09-20). Fetching a handful of candidates instead of
    # one lets the response name the applications it did not describe, so a
    # caller who asked about the injection can see they were handed the tablet.
    NAME_CANDIDATE_LIMIT = 5

    def _resolve_application(self, arguments: Dict[str, Any]):
        """Resolve a name or application number to one record plus a header.

        Returns ``(result, header, error_response)``; exactly one of ``result``
        and ``error_response`` is set. ``header`` identifies the application
        chosen and discloses the ones that matched but are not described.
        """
        drug_name, error = self._validate_optional_text(arguments, "drug_name")
        if error:
            return None, None, error
        application_number, error = self._validate_optional_text(
            arguments, "application_number"
        )
        if error:
            return None, None, error
        if drug_name and application_number:
            return (
                None,
                None,
                {
                    "status": "error",
                    "error": "Provide either drug_name or application_number, not both",
                },
            )
        if not drug_name and not application_number:
            return (
                None,
                None,
                {
                    "status": "error",
                    "error": "Either drug_name or application_number is required",
                },
            )

        if application_number:
            search = 'application_number:"{}"'.format(self._quoted(application_number))
            limit = 1
        else:
            search = build_drug_name_query(self._quoted(drug_name))
            limit = self.NAME_CANDIDATE_LIMIT

        requested = self._make_request(search, limit)
        if requested["status"] == "error":
            return None, None, requested
        data = requested.get("payload") or {}
        if not data.get("results"):
            return (
                None,
                None,
                {
                    "status": "error",
                    "error": "Drug not found in FDA approvals database",
                    "query": search,
                },
            )

        results = data["results"]
        total = data.get("meta", {}).get("results", {}).get("total", len(results))
        if application_number and total != 1:
            return (
                None,
                None,
                {
                    "status": "error",
                    "error": (
                        "Exact application_number query returned {} records; "
                        "cannot select a trustworthy application"
                    ).format(total),
                    "total_applications": total,
                    "query": search,
                },
            )
        # Only NAME_CANDIDATE_LIMIT records are fetched, so a name matching more
        # applications than that cannot list them all. Say so rather than
        # repeat the defect this module just removed from `strengths`: a list
        # cut short beside a count that implies it is complete.
        others = [r.get("application_number") for r in results[1:]]
        brand_name, generic_name = collect_names(results[0])
        brand_names, generic_names = collect_name_lists(results[0])
        header = {
            "query": search,
            "matching_applications": total,
            "other_matching_applications": others or None,
            "other_matching_applications_truncated": total - 1 > len(others),
            "application_number": results[0].get("application_number"),
            "sponsor_name": results[0].get("sponsor_name"),
            "brand_name": brand_name,
            "generic_name": generic_name,
            "brand_names": brand_names,
            "generic_names": generic_names,
        }
        return results[0], header, None

    def _extract_approval_summary(self, result: Dict) -> Dict:
        """Extract a summary from a drugsfda result."""
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

        brand_name, generic_name = collect_names(result)
        brand_names, generic_names = collect_name_lists(result)
        return {
            "application_number": result.get("application_number"),
            "sponsor_name": result.get("sponsor_name"),
            "brand_name": brand_name,
            "generic_name": generic_name,
            "brand_names": brand_names,
            "generic_names": generic_names,
            "active_ingredients": sorted(active_ingredients)
            if active_ingredients
            else None,
            "dosage_forms": sorted(dosage_forms) if dosage_forms else None,
            "routes": sorted(routes) if routes else None,
            # Every distinct strength, never a slice. This was
            # `sorted(strengths)[:5]` printed next to `product_count` with no
            # truncation flag, so NDA215256 advertised 12 products and showed 5
            # of its 7 strengths -- see `_strength_sort_key` for which two the
            # lexicographic cut deleted and why they were the worst two to lose.
            "strengths": sorted(strengths, key=_strength_sort_key)
            if strengths
            else None,
            "strength_count": len(strengths),
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
            parts.append(build_drug_name_query(self._quoted(drug_name)))
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
        result, header, error = self._resolve_application(arguments)
        if error:
            return error

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

        return {
            "status": "success",
            "data": dict(
                header,
                total_submissions=len(history),
                submission_history=history,
            ),
            "metadata": {
                "application_selection": (
                    "exact_application_number"
                    if header["query"].startswith("application_number:")
                    else "first_name_match"
                ),
                "matched_applications": header["matching_applications"],
                "search": header["query"],
                "all_submission_documents_included": True,
                "result_set_complete": True,
            },
        }

    def _get_approved_products(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get approved product details for a drug."""
        result, header, error = self._resolve_application(arguments)
        if error:
            return error

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

        return {
            "status": "success",
            "data": dict(
                header,
                total_products=len(formatted_products),
                products=formatted_products,
            ),
            "metadata": {
                "application_selection": (
                    "exact_application_number"
                    if header["query"].startswith("application_number:")
                    else "first_name_match"
                ),
                "matched_applications": header["matching_applications"],
                "search": header["query"],
                "result_set_complete": True,
            },
        }
