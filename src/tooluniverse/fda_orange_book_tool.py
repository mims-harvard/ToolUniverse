# fda_orange_book_tool.py

import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

FDA_BASE_URL = "https://api.fda.gov"


@register_tool("FDAOrangeBookTool")
class FDAOrangeBookTool(BaseTool):
    """
    FDA Orange Book and Drugs@FDA tool for drug approval information.

    Provides:
    - Drug approval history
    - Patent information
    - Exclusivity dates
    - Therapeutic equivalence (TE) codes
    - Generic availability
    - Regulatory review documents
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to operation handler."""
        operation = arguments.get("operation")
        # Auto-fill operation from tool config const if not provided by user
        if not operation:
            operation = self.get_schema_const_operation()

        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        if operation == "search_drug":
            operation_result = self._search_drug(arguments)
        elif operation == "get_approval_history":
            operation_result = self._get_approval_history(arguments)
        elif operation == "get_patent_info":
            operation_result = self._get_patent_info(arguments)
        elif operation == "get_exclusivity":
            operation_result = self._get_exclusivity(arguments)
        elif operation == "check_generic_availability":
            operation_result = self._check_generic_availability(arguments)
        elif operation == "get_te_code":
            operation_result = self._get_te_code(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

        return self._with_data_payload(operation_result)

    def _with_data_payload(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure successful operation responses include a standardized data wrapper."""
        if not isinstance(result, dict):
            return {"status": "success", "data": {"value": result}, "value": result}

        if result.get("status") != "success":
            return result

        if "data" in result:
            return result

        data = {k: v for k, v in result.items() if k != "status"}
        return {"status": "success", "data": data}

    def _search_drug(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for drugs by brand name, generic name, or application number."""
        try:
            # Build search query
            search_terms = []

            if arguments.get("brand_name"):
                search_terms.append(f'products.brand_name:"{arguments["brand_name"]}"')

            # Feature-81B-004: accept drug_name as alias for generic_name
            generic = arguments.get("generic_name") or arguments.get("drug_name")
            if generic:
                search_terms.append(f'products.active_ingredients.name:"{generic}"')

            if arguments.get("application_number"):
                search_terms.append(
                    f'application_number:"{arguments["application_number"]}"'
                )

            if not search_terms:
                return {
                    "status": "error",
                    "error": "Must provide brand_name, generic_name, or application_number",
                }

            search_query = "+AND+".join(search_terms)
            limit = arguments.get("limit", 10)

            url = f"{FDA_BASE_URL}/drug/drugsfda.json"
            params = {"search": search_query, "limit": min(limit, 100)}

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            # Extract key information
            drugs = []
            for result in results:
                drug_info = {
                    "application_number": result.get("application_number"),
                    "sponsor_name": result.get("sponsor_name"),
                    "products": [],
                }

                for product in result.get("products", []):
                    product_info = {
                        "brand_name": product.get("brand_name"),
                        "active_ingredients": product.get("active_ingredients", []),
                        "dosage_form": product.get("dosage_form"),
                        "route": product.get("route"),
                        "marketing_status": product.get("marketing_status"),
                        "reference_drug": product.get("reference_drug"),
                        "te_code": product.get("te_code"),
                    }
                    drug_info["products"].append(product_info)

                drugs.append(drug_info)

            return {
                "status": "success",
                "drugs": drugs,
                "count": len(drugs),
                "total": data.get("meta", {}).get("results", {}).get("total", 0),
            }

        except requests.exceptions.Timeout:
            return {"status": "error", "error": "Request timeout after 30s"}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"HTTP {e.response.status_code}: {str(e)}",
            }
        except Exception as e:
            return {"status": "error", "error": f"Search failed: {str(e)}"}

    def _get_approval_history(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get approval history and submission details for an application."""
        try:
            app_number = arguments.get("application_number")
            if not app_number:
                return {
                    "status": "error",
                    "error": "Missing required parameter: application_number",
                }

            url = f"{FDA_BASE_URL}/drug/drugsfda.json"
            params = {"search": f'application_number:"{app_number}"', "limit": 1}

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            if not results:
                return {
                    "status": "error",
                    "error": f"No application found for {app_number}",
                }

            result = results[0]

            # Extract approval history
            submissions = result.get("submissions", [])
            approval_history = []

            for sub in submissions:
                submission_info = {
                    "submission_type": sub.get("submission_type"),
                    "submission_number": sub.get("submission_number"),
                    "submission_status": sub.get("submission_status"),
                    "submission_status_date": sub.get("submission_status_date"),
                    "review_priority": sub.get("review_priority"),
                    "submission_class": sub.get("submission_class_code_description"),
                    "documents": [],
                }

                # Add application documents
                for doc in sub.get("application_docs", []):
                    submission_info["documents"].append(
                        {
                            "type": doc.get("type"),
                            "url": doc.get("url"),
                            "date": doc.get("date"),
                        }
                    )

                approval_history.append(submission_info)

            # Find original approval
            original_approval = next(
                (s for s in submissions if s.get("submission_type") == "ORIG"), None
            )

            return {
                "status": "success",
                "application_number": app_number,
                "sponsor_name": result.get("sponsor_name"),
                "original_approval_date": original_approval.get(
                    "submission_status_date"
                )
                if original_approval
                else None,
                "submissions": approval_history,
                "submission_count": len(approval_history),
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"API request failed: {str(e)}"}
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to get approval history: {str(e)}",
            }

    def _get_patent_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get patent information for a drug (Note: Full patent data requires Orange Book download)."""
        try:
            app_number = arguments.get("application_number")
            brand_name = arguments.get("brand_name")

            if not app_number and not brand_name:
                return {
                    "status": "error",
                    "error": "Must provide application_number or brand_name",
                }

            # Search for the drug
            search_result = self._search_drug(arguments)
            if search_result.get("status") != "success":
                return search_result

            drugs = search_result.get("drugs", [])
            if not drugs:
                return {"status": "error", "error": "No drugs found matching criteria"}

            # Note: Drugs@FDA API doesn't include full patent details
            # Full patent info requires Orange Book data download
            return {
                "status": "success",
                "note": "Full patent information requires Orange Book data files from FDA",
                "download_url": "https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files",
                "drugs": drugs,
                "recommendation": "Use Orange Book downloadable data files for patent numbers and expiration dates",
            }

        except Exception as e:
            return {"status": "error", "error": f"Failed to get patent info: {str(e)}"}

    def _get_exclusivity(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get exclusivity information for a drug."""
        try:
            app_number = arguments.get("application_number")
            brand_name = arguments.get("brand_name")

            if not app_number and not brand_name:
                return {
                    "status": "error",
                    "error": "Must provide application_number or brand_name",
                }

            # Search for the drug
            search_result = self._search_drug(arguments)
            if search_result.get("status") != "success":
                return search_result

            drugs = search_result.get("drugs", [])
            if not drugs:
                return {"status": "error", "error": "No drugs found matching criteria"}

            # Note: Drugs@FDA API has limited exclusivity data
            # Full exclusivity details in Orange Book data files
            return {
                "status": "success",
                "note": "Full exclusivity details require Orange Book data files from FDA",
                "download_url": "https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files",
                "drugs": drugs,
                "exclusivity_types": [
                    "NCE (New Chemical Entity) - 5 years",
                    "New Clinical Study - 3 years",
                    "Orphan Drug - 7 years",
                    "Pediatric - 6 month extension",
                    "Patent Challenge - 180 days",
                ],
                "recommendation": "Check Orange Book exclusivity.txt file for dates",
            }

        except Exception as e:
            return {"status": "error", "error": f"Failed to get exclusivity: {str(e)}"}

    def _check_generic_availability(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Check if generic versions are approved/available."""
        try:
            brand_name = arguments.get("brand_name")
            generic_name = arguments.get("generic_name") or arguments.get("drug_name")

            if not brand_name and not generic_name:
                return {
                    "status": "error",
                    "error": "Must provide brand_name, generic_name, or drug_name",
                }

            # Step 1: Search by brand_name/generic_name to find the reference drug.
            # Use limit=100 to avoid missing reference drugs beyond the default 10.
            search_result = self._search_drug({**arguments, "limit": 100})
            if search_result.get("status") != "success":
                return search_result

            drugs = search_result.get("drugs", [])

            # Step 2: If brand_name was used, extract active ingredient and do a
            # broader ingredient-based search to capture ANDA generics (which have
            # different brand names than the originator NDA).
            if brand_name and not generic_name:
                active_ingredient = None
                for drug in drugs:
                    for product in drug.get("products", []):
                        ingredients = product.get("active_ingredients", [])
                        if ingredients:
                            active_ingredient = ingredients[0].get("name")
                            break
                    if active_ingredient:
                        break

                if active_ingredient:
                    ingredient_result = self._search_drug(
                        {"generic_name": active_ingredient, "limit": 100}
                    )
                    if ingredient_result.get("status") == "success":
                        # Merge, deduplicating by application_number
                        seen = {d["application_number"] for d in drugs}
                        for d in ingredient_result.get("drugs", []):
                            if d["application_number"] not in seen:
                                drugs.append(d)
                                seen.add(d["application_number"])

            # Categorize reference vs generic products (one entry per application number)
            reference_drugs = []
            generic_drugs = []
            seen_ref_apps: set = set()
            seen_gen_apps: set = set()

            for drug in drugs:
                app_num = drug.get("application_number", "")
                for product in drug.get("products", []):
                    if product.get("reference_drug") == "Yes":
                        if app_num not in seen_ref_apps:
                            seen_ref_apps.add(app_num)
                            reference_drugs.append(
                                {
                                    "application_number": app_num,
                                    "brand_name": product.get("brand_name"),
                                    "sponsor": drug.get("sponsor_name"),
                                    "marketing_status": product.get("marketing_status"),
                                }
                            )
                    else:
                        if app_num not in seen_gen_apps:
                            seen_gen_apps.add(app_num)
                            generic_drugs.append(
                                {
                                    "application_number": app_num,
                                    "brand_name": product.get("brand_name")
                                    or "Generic",
                                    "sponsor": drug.get("sponsor_name"),
                                    "marketing_status": product.get("marketing_status"),
                                    "te_code": product.get("te_code"),
                                }
                            )

            return {
                "status": "success",
                "reference_drugs": reference_drugs,
                "reference_count": len(reference_drugs),
                "generic_drugs": generic_drugs,
                "generic_count": len(generic_drugs),
                "generics_available": len(generic_drugs) > 0,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to check generic availability: {str(e)}",
            }

    def _get_te_code(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get therapeutic equivalence (TE) code information."""
        try:
            brand_name = arguments.get("brand_name")
            generic_name = arguments.get("generic_name")

            if not brand_name and not generic_name:
                return {
                    "status": "error",
                    "error": "Must provide brand_name or generic_name",
                }

            # Search for products
            search_result = self._search_drug(arguments)
            if search_result.get("status") != "success":
                return search_result

            drugs = search_result.get("drugs", [])

            # Extract TE codes
            te_codes = []
            for drug in drugs:
                for product in drug.get("products", []):
                    te_code = product.get("te_code")
                    if te_code:
                        te_codes.append(
                            {
                                "brand_name": product.get("brand_name"),
                                "te_code": te_code,
                                "application_number": drug.get("application_number"),
                                "interpretation": self._interpret_te_code(te_code),
                                "reference_drug": product.get("reference_drug"),
                            }
                        )

            return {
                "status": "success",
                "te_codes": te_codes,
                "count": len(te_codes),
                "te_code_guide": {
                    "AB": "Therapeutically equivalent, meets bioequivalence requirements",
                    "AT": "Therapeutically equivalent, meets bioequivalence standards (topical)",
                    "AP": "Therapeutically equivalent, pharmaceutical equivalents (solution/powder)",
                    "BC": "Drug product administered systemically, delayed-onset, specific rates not significant",
                    "BD": "Active ingredients and dosage forms not pharmaceutical equivalent",
                    "BN": "Product in solution, does not meet bioequivalence",
                    "BP": "No bioequivalence required, but concerns about quality/standards",
                    "BR": "Suppository/enema not bioequivalent to oral form",
                    "BS": "Standard deficiency exists",
                    "BT": "Bioequivalence issues for topical products",
                    "BX": "Insufficient data for therapeutic equivalence determination",
                },
            }

        except Exception as e:
            return {"status": "error", "error": f"Failed to get TE code: {str(e)}"}

    def _interpret_te_code(self, te_code: str) -> str:
        """Interpret TE code meaning."""
        if not te_code:
            return "No TE code assigned"

        first_letter = te_code[0]

        if first_letter == "A":
            return "Therapeutically equivalent - Products expected to have same clinical effect and safety profile"
        elif first_letter == "B":
            return "NOT therapeutically equivalent - Products may not have same clinical effect or may have different safety profiles"
        else:
            return f"Unknown TE code: {te_code}"
