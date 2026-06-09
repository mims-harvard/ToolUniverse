"""
ZINC22 / CartBlanche Tool - Commercially Available Compounds for Virtual Screening

Provides access to the ZINC22 database via the CartBlanche22 REST API for
retrieving and structure-searching commercially available small molecules used
in virtual screening, drug discovery, and chemical biology.

ZINC22 contains billions of make-on-demand and in-stock purchasable compounds
with SMILES, computed properties (MW, LogP, heavy atoms, rings, InChI/InChIKey),
and vendor/catalog (purchasability + price) information.

API base: https://cartblanche22.docking.org
No authentication required. (Replaces the retired zinc15.docking.org service,
which now serves a bot-verification HTML wall for every endpoint.)

Reference: Tingle et al., ZINC-22, J. Chem. Inf. Model. 2023.
"""

import time
import requests
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool
from .tool_registry import register_tool


ZINC_BASE_URL = "https://cartblanche22.docking.org"


@register_tool("ZincTool")
class ZincTool(BaseTool):
    """
    Tool for querying the ZINC22 database of commercially available compounds
    via the CartBlanche22 API.

    ZINC22 is a free database of commercially-available compounds for virtual
    screening, maintained by the Irwin and Shoichet labs at UCSF.

    Supported operations:
    - get_compound: Get details for a ZINC ID (structure + computed properties)
    - get_purchasable: Get the vendor/catalog (purchasability + price) list for a ZINC ID
    - search_by_smiles: Structure search by SMILES (exact or similarity)
    - search_compounds: NOT supported by CartBlanche22 (no free-text/name search)
    - search_by_properties: NOT supported by CartBlanche22 (no property-range search)
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (compatible; ToolUniverse/1.0)"}
        )
        self.timeout = 30

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the ZINC22/CartBlanche tool with given arguments."""
        operation = arguments.get("operation")
        if not operation:
            return {
                "status": "error",
                "error": "Missing required parameter: operation",
            }

        operation_handlers = {
            "get_compound": self._get_compound,
            "get_purchasable": self._get_purchasable,
            "search_by_smiles": self._search_by_smiles,
            "search_compounds": self._unsupported_name_search,
            "search_by_properties": self._unsupported_property_search,
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
            return {
                "status": "error",
                "error": "ZINC22 (CartBlanche) request timed out",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to ZINC22 (CartBlanche) API",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": "ZINC22 operation failed: {}".format(str(e)),
            }

    # ------------------------------------------------------------------ #
    # HTTP helpers
    # ------------------------------------------------------------------ #
    def _get_json(self, url: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """GET a URL and return parsed JSON wrapped in an {ok, ...} envelope."""
        response = self.session.get(url, params=params or {}, timeout=self.timeout)
        if response.status_code == 404:
            return {"ok": False, "status_code": 404, "error": "Resource not found"}
        if response.status_code != 200:
            return {
                "ok": False,
                "status_code": response.status_code,
                "error": "CartBlanche API returned status {}".format(
                    response.status_code
                ),
            }
        try:
            return {"ok": True, "data": response.json()}
        except ValueError:
            return {
                "ok": False,
                "status_code": 200,
                "error": "Invalid (non-JSON) response from CartBlanche API",
                "response_snippet": response.text[:200],
            }

    @staticmethod
    def _normalize_zinc_id(zinc_id: str) -> str:
        """Normalize a ZINC ID to canonical 'ZINC' + 12-digit/code form."""
        zinc_id = str(zinc_id).strip()
        if not zinc_id.upper().startswith("ZINC"):
            zinc_id = "ZINC" + zinc_id
        # Preserve case for ZINC22 alphanumeric IDs; uppercase the 'ZINC' prefix.
        return "ZINC" + zinc_id[4:]

    def _fetch_substance(self, zinc_id: str) -> Dict[str, Any]:
        """Fetch the raw /substance/{id}.json record."""
        url = "{}/substance/{}.json".format(ZINC_BASE_URL, zinc_id)
        return self._get_json(url)

    def _resolve_substance(self, raw_id: Any) -> Dict[str, Any]:
        """Validate a ZINC ID, fetch its substance record, and normalize errors.

        Returns ``{"ok": True, "zinc_id": ..., "substance": ...}`` on success,
        or ``{"ok": False, "error": {...}}`` carrying a ready-to-return
        ``{status: error}`` envelope shared by _get_compound / _get_purchasable.
        """
        if not raw_id:
            return {
                "ok": False,
                "error": {"status": "error", "error": "zinc_id parameter is required"},
            }

        zinc_id = self._normalize_zinc_id(raw_id)
        result = self._fetch_substance(zinc_id)
        if not result["ok"]:
            if result.get("status_code") == 404:
                message = "Compound {} not found in ZINC22".format(zinc_id)
            else:
                message = result["error"]
            return {"ok": False, "error": {"status": "error", "error": message}}

        return {"ok": True, "zinc_id": zinc_id, "substance": result["data"]}

    # ------------------------------------------------------------------ #
    # Operation handlers
    # ------------------------------------------------------------------ #
    def _get_compound(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get structure + computed properties for a ZINC ID."""
        resolved = self._resolve_substance(arguments.get("zinc_id"))
        if not resolved["ok"]:
            return resolved["error"]

        zinc_id = resolved["zinc_id"]
        sub = resolved["substance"]
        tranche = sub.get("tranche_details") or {}
        catalogs = sub.get("catalogs") or []

        compound = {
            "zinc_id": sub.get("zinc_id", zinc_id),
            "smiles": sub.get("smiles"),
            "formula": sub.get("mol_formula"),
            "mwt": tranche.get("mwt"),
            "logp": tranche.get("logp"),
            "heavy_atoms": tranche.get("heavy_atoms"),
            "hetero_atoms": sub.get("hetero_atoms"),
            "rings": sub.get("rings"),
            "inchi": tranche.get("inchi"),
            "inchikey": tranche.get("inchikey"),
            "database": sub.get("db"),
            "n_catalogs": len(catalogs),
        }

        return {
            "status": "success",
            "data": compound,
        }

    def _get_purchasable(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Return the vendor/catalog (purchasability + price) list for a ZINC ID."""
        resolved = self._resolve_substance(arguments.get("zinc_id"))
        if not resolved["ok"]:
            return resolved["error"]

        zinc_id = resolved["zinc_id"]
        sub = resolved["substance"]
        catalogs = sub.get("catalogs") or []

        vendors = []
        for cat in catalogs:
            vendors.append(
                {
                    "catalog_name": cat.get("catalog_name"),
                    "supplier_code": cat.get("supplier_code"),
                    "price": cat.get("price"),
                    "quantity": cat.get("quantity"),
                    "unit": cat.get("unit"),
                    "shipping": cat.get("shipping"),
                    "purchasable": bool(cat.get("purchase")),
                    "url": cat.get("url"),
                }
            )

        return {
            "status": "success",
            "data": {
                "zinc_id": sub.get("zinc_id", zinc_id),
                "smiles": sub.get("smiles"),
                "vendor_count": len(vendors),
                "vendors": vendors,
            },
        }

    def _search_by_smiles(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Structure-search ZINC22/ZINC20 by SMILES (exact or similarity).

        CartBlanche structure search is asynchronous: submit the SMILES to
        /smiles.json (multipart form) to get a task id, then poll
        /search/result/{task} until status == SUCCESS.
        """
        smiles = arguments.get("smiles")
        if not smiles:
            return {"status": "error", "error": "smiles parameter is required"}

        dist = arguments.get("dist", 0)
        adist = arguments.get("adist", 0)
        database = arguments.get("database", "zinc20,zinc22")
        count = arguments.get("count", 10)

        # 1) Submit the search job.
        submit_url = "{}/smiles.json".format(ZINC_BASE_URL)
        form = {
            "smiles": (None, str(smiles)),
            "dist": (None, str(dist)),
            "adist": (None, str(adist)),
            "database": (None, str(database)),
        }
        try:
            submit_resp = self.session.get(submit_url, files=form, timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": "Failed to submit structure search: {}".format(str(e)),
            }

        if submit_resp.status_code != 200:
            return {
                "status": "error",
                "error": "Structure search submission returned status {}".format(
                    submit_resp.status_code
                ),
            }
        try:
            task_id = submit_resp.json().get("task")
        except ValueError:
            return {
                "status": "error",
                "error": "Structure search submission did not return a task id "
                "(SMILES may be invalid)",
                "response_snippet": submit_resp.text[:200],
            }
        if not task_id:
            return {
                "status": "error",
                "error": "Structure search submission did not return a task id",
            }

        # 2) Poll for the result.
        result_url = "{}/search/result/{}".format(ZINC_BASE_URL, task_id)
        deadline = time.time() + self.timeout
        result_payload = None
        while time.time() < deadline:
            poll = self._get_json(result_url)
            if not poll["ok"]:
                return {"status": "error", "error": poll["error"]}
            payload = poll["data"]
            poll_status = payload.get("status") if isinstance(payload, dict) else None
            if poll_status == "SUCCESS":
                result_payload = payload.get("result", {})
                break
            if poll_status == "FAILURE":
                return {
                    "status": "error",
                    "error": "CartBlanche structure search failed (task {})".format(
                        task_id
                    ),
                }
            time.sleep(2)

        if result_payload is None:
            return {
                "status": "error",
                "error": "Structure search did not complete within {}s "
                "(task {}). Try again or widen the distance.".format(
                    self.timeout, task_id
                ),
            }

        matches = self._collect_matches(result_payload, count)

        return {
            "status": "success",
            "data": matches,
            "count": len(matches),
            "query_smiles": smiles,
            "dist": dist,
            "adist": adist,
        }

    @staticmethod
    def _collect_matches(result_payload: Any, count: int) -> List[Dict[str, Any]]:
        """Flatten zinc20/zinc22 hit lists into a clean match record list.

        CartBlanche returns ``result`` either as an empty list (no grouped
        hits) or as a dict keyed by database name (``zinc22``/``zinc20``),
        each value being a list of hit rows.
        """
        matches: List[Dict[str, Any]] = []
        if not isinstance(result_payload, dict):
            return matches
        for db_key in ("zinc22", "zinc20"):
            rows = result_payload.get(db_key)
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                tranche = row.get("tranche_details") or {}
                matches.append(
                    {
                        "zinc_id": row.get("zinc_id") or row.get("identifier"),
                        "smiles": row.get("smiles") or row.get("hitSmiles"),
                        "matched_smiles": row.get("matched_smiles"),
                        "formula": row.get("mol_formula"),
                        "mwt": tranche.get("mwt"),
                        "logp": tranche.get("logp"),
                        "inchikey": tranche.get("inchikey"),
                        "database": row.get("db", db_key),
                        "n_catalogs": len(row.get("catalogs") or []),
                    }
                )
                if len(matches) >= count:
                    return matches
        return matches

    def _unsupported_name_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Free-text / name search is not offered by CartBlanche22."""
        return {
            "status": "error",
            "error": "Name/free-text compound search is not supported by ZINC22 "
            "(CartBlanche22). ZINC is structure- and ID-centric. Use "
            "ZINC_search_by_smiles with a SMILES string to find compounds, "
            "or ZINC_get_compound / ZINC_get_purchasable with a known ZINC ID.",
            "supported_search": "search_by_smiles (structure search by SMILES)",
        }

    def _unsupported_property_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Molecular-property-range search is not offered by CartBlanche22."""
        return {
            "status": "error",
            "error": "Molecular-property-range search is not supported by ZINC22 "
            "(CartBlanche22). CartBlanche only offers structure search "
            "(by SMILES/SMARTS), ZINC-ID lookup, and supplier lookup. Use "
            "ZINC_search_by_smiles to find compounds by structure, then "
            "ZINC_get_compound to read each hit's MW/LogP and filter client-side.",
            "supported_search": "search_by_smiles (structure search by SMILES)",
        }
