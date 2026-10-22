# fda_orange_book_tool.py

import os
import re
import threading
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import requests
from .base_tool import BaseTool
from .tool_registry import register_tool

FDA_BASE_URL = "https://api.fda.gov"

# Patents and exclusivity come from FDA's monthly Orange Book data files, not
# from openFDA. Drugs@FDA has no patent data, and openFDA's /drug/orangebook
# endpoint keeps one use code per product-patent pair and one date per
# exclusivity code, so it drops facts the files list (FDA/openfda#225).
# The tool does not download the files. fda.gov redirects a scripted request
# for them (the default python-requests client) to an abuse-detection page, so
# a person downloads the zip from ORANGE_BOOK_PAGE_URL and sets the environment
# variable below to the zip or to the folder it was extracted into.
ORANGE_BOOK_ENV = "TOOLUNIVERSE_ORANGE_BOOK_DATA"
ORANGE_BOOK_PAGE_URL = (
    "https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files"
)
_ORANGE_BOOK_FILES = ("products.txt", "patent.txt", "exclusivity.txt")
_orange_book_cache: Dict[str, Any] = {}
_orange_book_lock = threading.Lock()

# openFDA joins search clauses with a literal " AND "/" OR " (the operator must
# survive URL-encoding as a real space). Writing "+AND+" into a requests params
# dict encodes it as "%2BAND%2B", which openFDA cannot parse and answers with a
# 404 -- so the separator has to be a plain space-delimited operator.
_AND = " AND "
_OR = " OR "


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

    @staticmethod
    def _openfda_get(params: Dict[str, Any]) -> Dict[str, Any]:
        """GET Drugs@FDA, translating openFDA's "404 == zero matches" convention.

        openFDA answers a well-formed query that matches nothing with HTTP 404 and
        a body of {"error": {"code": "NOT_FOUND", ...}} rather than an empty 200
        (verified live: /drug/drugsfda.json?search=products.active_ingredients.name:
        "Quviviq" -> 404 {"error":{"code":"NOT_FOUND","message":"No matches
        found!"}}). Reporting that as a transport failure makes "no such product"
        indistinguishable from "the API is down", so an explicit NOT_FOUND body is
        translated into an empty result set. A 404 *without* that body is still a
        real error, so a genuinely missing endpoint is not silently swallowed.
        """
        response = requests.get(
            f"{FDA_BASE_URL}/drug/drugsfda.json", params=params, timeout=30
        )
        if response.status_code == 404:
            try:
                code = (response.json().get("error") or {}).get("code")
            except ValueError:
                code = None
            if code == "NOT_FOUND":
                return {"results": [], "meta": {"results": {"total": 0}}}
        response.raise_for_status()
        return response.json()

    def _search_drug(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for drugs by brand name, generic name, or application number."""
        try:
            # Build search query
            search_terms = []

            if arguments.get("brand_name"):
                search_terms.append(f'products.brand_name:"{arguments["brand_name"]}"')

            if arguments.get("generic_name"):
                search_terms.append(
                    f'products.active_ingredients.name:"{arguments["generic_name"]}"'
                )

            # Feature-81B-004: drug_name is the caller-friendly "name of any kind"
            # parameter this tool's description advertises ("by brand name, generic
            # name, or application number"). It used to be a plain alias for
            # generic_name, which meant a brand name passed here searched only the
            # active-ingredient field and could never match. It now matches either
            # field, so the parameter behaves the way its name reads.
            drug_name = arguments.get("drug_name")
            if drug_name:
                search_terms.append(
                    f'(products.brand_name:"{drug_name}"'
                    f'{_OR}products.active_ingredients.name:"{drug_name}")'
                )

            if arguments.get("application_number"):
                search_terms.append(
                    f'application_number:"{arguments["application_number"]}"'
                )

            if not search_terms:
                return {
                    "status": "error",
                    "error": (
                        "Must provide at least one of: brand_name, generic_name, "
                        "drug_name, or application_number"
                    ),
                }

            search_query = _AND.join(search_terms)
            limit = arguments.get("limit", 10)

            params = {"search": search_query, "limit": min(limit, 100)}

            data = self._openfda_get(params)
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

            payload = {
                "status": "success",
                "drugs": drugs,
                "count": len(drugs),
                "total": data.get("meta", {}).get("results", {}).get("total", 0),
            }
            if not drugs:
                payload["note"] = (
                    "No Drugs@FDA records matched this query. This is an empty "
                    "result, not an API failure. Check spelling, or try the other "
                    "name form (brand_name vs generic_name)."
                )
            return payload

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

            data = self._openfda_get(
                {"search": f'application_number:"{app_number}"', "limit": 1}
            )
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

    @staticmethod
    def _parse_ob_date(text: str) -> Optional[str]:
        """'May 31, 2033' -> '2033-05-31'. Blank -> None; unparseable text is kept."""
        text = (text or "").strip()
        if not text:
            return None
        try:
            return datetime.strptime(text, "%b %d, %Y").date().isoformat()
        except ValueError:
            return text

    @staticmethod
    def _parse_ob_rows(raw: bytes) -> List[Dict[str, str]]:
        lines = raw.decode("latin-1").splitlines()
        header = lines[0].split("~")
        return [dict(zip(header, line.split("~"))) for line in lines[1:] if line]

    @staticmethod
    def _read_ob_source(path: Path) -> Tuple[Dict[str, bytes], List[str]]:
        """Raw bytes of the three data files and their file dates, from a zip or folder."""
        raw: Dict[str, bytes] = {}
        dates: List[str] = []
        if path.is_dir():
            for name in _ORANGE_BOOK_FILES:
                member = next(
                    (f for f in path.iterdir() if f.name.lower() == name), None
                )
                if member is None:
                    raise ValueError(f"{name} not found in {path}")
                raw[name] = member.read_bytes()
                dates.append(date.fromtimestamp(member.stat().st_mtime).isoformat())
            return raw, dates
        with zipfile.ZipFile(path) as zf:
            for name in _ORANGE_BOOK_FILES:
                info = next(
                    (i for i in zf.infolist() if i.filename.lower().endswith(name)),
                    None,
                )
                if info is None:
                    raise ValueError(f"{name} not found in {path}")
                raw[name] = zf.read(info)
                dates.append(datetime(*info.date_time).date().isoformat())
        return raw, dates

    def _load_orange_book(self) -> Dict[str, Any]:
        """Index the local Orange Book data files.

        The index is cached per process and rebuilt when the file or folder changes.
        """
        configured = os.environ.get(ORANGE_BOOK_ENV, "").strip()
        if not configured:
            raise FileNotFoundError(
                f"{ORANGE_BOOK_ENV} is not set; download the Orange Book data files "
                f"zip from {ORANGE_BOOK_PAGE_URL} and set {ORANGE_BOOK_ENV} to the "
                "zip or to the folder it was extracted into"
            )
        path = Path(configured).expanduser()
        if not path.exists():
            raise FileNotFoundError(
                f"{ORANGE_BOOK_ENV} points to {path}, which does not exist"
            )
        with _orange_book_lock:
            # A folder's own mtime misses files overwritten in place.
            members = sorted(path.iterdir()) if path.is_dir() else [path]
            stamp = (str(path), tuple(m.stat().st_mtime_ns for m in members))
            cached = _orange_book_cache.get("data")
            if cached and cached["stamp"] == stamp:
                return cached

            raw, dates = self._read_ob_source(path)

            products: Dict[Tuple[str, str, str], Dict[str, str]] = {}
            for row in self._parse_ob_rows(raw["products.txt"]):
                key = (row["Appl_Type"], row["Appl_No"], row["Product_No"])
                products[key] = row

            patents: Dict[Tuple[str, str, str], Dict[Tuple[str, str], Dict]] = {}
            for row in self._parse_ob_rows(raw["patent.txt"]):
                key = (row["Appl_Type"], row["Appl_No"], row["Product_No"])
                patent_no = row["Patent_No"]
                expires = self._parse_ob_date(row["Patent_Expire_Date_Text"])
                # One file row per use code: fold them into one patent entry.
                entry = patents.setdefault(key, {}).setdefault(
                    (patent_no, expires or ""),
                    {
                        "patent_number": patent_no,
                        "expiration_date": expires,
                        "pediatric_extension": patent_no.endswith("*PED"),
                        "drug_substance": row["Drug_Substance_Flag"] == "Y",
                        "drug_product": row["Drug_Product_Flag"] == "Y",
                        "use_codes": [],
                        "delist_requested": row["Delist_Flag"] == "Y",
                        "submission_date": self._parse_ob_date(row["Submission_Date"]),
                    },
                )
                code = row["Patent_Use_Code"].strip()
                if code and code not in entry["use_codes"]:
                    entry["use_codes"].append(code)

            exclusivity: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
            for row in self._parse_ob_rows(raw["exclusivity.txt"]):
                key = (row["Appl_Type"], row["Appl_No"], row["Product_No"])
                item = {
                    "code": row["Exclusivity_Code"],
                    "expiration_date": self._parse_ob_date(row["Exclusivity_Date"]),
                }
                if item not in exclusivity.setdefault(key, []):
                    exclusivity[key].append(item)

            data = {
                "stamp": stamp,
                "products": products,
                "patents": patents,
                "exclusivity": exclusivity,
                "source": {
                    "name": "FDA Orange Book data files",
                    "path": str(path),
                    "page": ORANGE_BOOK_PAGE_URL,
                    "files_dated": max(dates),
                },
            }
            _orange_book_cache["data"] = data
            return data

    @staticmethod
    def _parse_application_number(value: str) -> Optional[Tuple[Optional[str], str]]:
        """'NDA021695', 'N021695', '021695' or '21695' -> ('N'|'A'|None, '021695')."""
        match = re.fullmatch(
            r"(NDA|ANDA|N|A)?\s*-?\s*0*(\d{1,6})", (value or "").strip().upper()
        )
        if not match:
            return None
        prefix = match.group(1)
        appl_type = {"NDA": "N", "N": "N", "ANDA": "A", "A": "A"}.get(prefix)
        return appl_type, match.group(2).zfill(6)

    def _match_ob_products(
        self, ob: Dict[str, Any], arguments: Dict[str, Any]
    ) -> Tuple[Optional[List[Tuple[str, str, str]]], Optional[str]]:
        app_number = arguments.get("application_number")
        brand_name = (arguments.get("brand_name") or "").strip().upper()
        if not app_number and not brand_name:
            return None, "Must provide application_number or brand_name"

        parsed = None
        if app_number:
            parsed = self._parse_application_number(str(app_number))
            if parsed is None:
                return None, (
                    f"Unrecognized application_number {app_number!r}; "
                    "use a form like NDA021695, N021695 or 021695"
                )

        keys = []
        for key, row in ob["products"].items():
            if parsed and (key[1] != parsed[1] or (parsed[0] and key[0] != parsed[0])):
                continue
            if brand_name and row["Trade_Name"].strip().upper() != brand_name:
                continue
            keys.append(key)
        return sorted(keys), None

    def _ob_product_summary(self, ob: Dict[str, Any], key) -> Dict[str, Any]:
        row = ob["products"][key]
        return {
            "application_number": f"{key[0]}{key[1]}",
            "product_number": key[2],
            "trade_name": row["Trade_Name"],
            "ingredient": row["Ingredient"],
            "strength": row["Strength"],
            "applicant": row["Applicant_Full_Name"] or row["Applicant"],
            "marketing_category": row["Type"],
        }

    def _get_patent_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Patents listed in the Orange Book for each matching product."""
        try:
            ob = self._load_orange_book()
            keys, error = self._match_ob_products(ob, arguments)
            if error:
                return {"status": "error", "error": error}

            products = []
            for key in keys:
                summary = self._ob_product_summary(ob, key)
                summary["patents"] = sorted(
                    ob["patents"].get(key, {}).values(),
                    key=lambda p: (p["expiration_date"] or "", p["patent_number"]),
                )
                products.append(summary)

            payload = {
                "status": "success",
                "products": products,
                "count": len(products),
                "patent_count": sum(len(p["patents"]) for p in products),
                "source": ob["source"],
            }
            if not products:
                payload["note"] = (
                    "No Orange Book product matched. The Orange Book covers NDA and "
                    "ANDA drug products, not biologics (see the Purple Book)."
                )
            elif not payload["patent_count"]:
                payload["note"] = "No patents are listed for the matched products."
            return payload

        except Exception as e:
            return {"status": "error", "error": f"Failed to get patent info: {str(e)}"}

    def _get_exclusivity(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Exclusivity codes and expiration dates listed for each matching product."""
        try:
            ob = self._load_orange_book()
            keys, error = self._match_ob_products(ob, arguments)
            if error:
                return {"status": "error", "error": error}

            products = []
            for key in keys:
                summary = self._ob_product_summary(ob, key)
                summary["exclusivity"] = sorted(
                    ob["exclusivity"].get(key, []),
                    key=lambda x: (x["expiration_date"] or "", x["code"]),
                )
                products.append(summary)

            payload = {
                "status": "success",
                "products": products,
                "count": len(products),
                "exclusivity_count": sum(len(p["exclusivity"]) for p in products),
                "source": ob["source"],
            }
            if not products:
                payload["note"] = (
                    "No Orange Book product matched. The Orange Book covers NDA and "
                    "ANDA drug products, not biologics (see the Purple Book)."
                )
            elif not payload["exclusivity_count"]:
                payload["note"] = "No exclusivity is listed for the matched products."
            return payload

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
