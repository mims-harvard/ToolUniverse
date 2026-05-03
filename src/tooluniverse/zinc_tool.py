"""
ZINC Database Tool - Commercially Available Compounds for Virtual Screening

Provides access to the ZINC15/20 database REST API for searching and retrieving
information about commercially available small molecules for virtual screening,
drug discovery, and chemical biology.

ZINC contains over 750 million purchasable compounds with SMILES, molecular
properties (MW, LogP, HBD, HBA, rotatable bonds), and vendor/catalog information.

API base: https://zinc15.docking.org
No authentication required.

Reference: Sterling & Irwin, J. Chem. Inf. Model. 2015; Irwin et al., J. Chem. Inf. Model. 2020
"""

import requests
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool
from .tool_registry import register_tool


ZINC_BASE_URL = "https://zinc15.docking.org"


@register_tool("ZincTool")
class ZincTool(BaseTool):
    """
    Tool for querying the ZINC database of commercially available compounds.

    ZINC is a free database of commercially-available compounds for virtual
    screening, maintained by the Irwin and Shoichet labs at UCSF.

    Supported operations:
    - search_compounds: Search by name or keyword
    - get_compound: Get details for a ZINC ID (properties + vendors)
    - search_by_smiles: Search by SMILES string (exact or substructure)
    - get_purchasable: Browse purchasable compounds by availability tier
    - search_by_properties: Filter compounds by molecular properties
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.session = requests.Session()
        # ZINC blocks default Python requests User-Agent with 403
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (compatible; ToolUniverse/1.0)"}
        )
        self.timeout = 30

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the ZINC API tool with given arguments."""
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        operation_handlers = {
            "search_compounds": self._search_compounds,
            "get_compound": self._get_compound,
            "search_by_smiles": self._search_by_smiles,
            "get_purchasable": self._get_purchasable,
            "search_by_properties": self._search_by_properties,
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
            return {"status": "error", "error": "ZINC API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to ZINC API"}
        except Exception as e:
            return {
                "status": "error",
                "error": "ZINC operation failed: {}".format(str(e)),
            }

    def _make_request(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make GET request to ZINC API."""
        url = "{}/{}".format(ZINC_BASE_URL, path)
        response = self.session.get(url, params=params or {}, timeout=self.timeout)
        if response.status_code == 200:
            try:
                data = response.json()
                return {"ok": True, "data": data}
            except ValueError:
                ct = response.headers.get("content-type", "")
                return {
                    "ok": False,
                    "error": "Invalid JSON response from ZINC API",
                    "content_type": ct,
                    "response_snippet": response.text[:200],
                    "retryable": "text/html" in ct
                    or response.text.lstrip().startswith("<"),
                    "suggestion": "ZINC API may be under maintenance. Retry in a few minutes.",
                }
        elif response.status_code == 404:
            return {"ok": False, "error": "Resource not found"}
        elif response.status_code == 500:
            return {"ok": False, "error": "ZINC API internal server error"}
        else:
            return {
                "ok": False,
                "error": "ZINC API returned status {}".format(response.status_code),
            }

    def _enrich_with_properties(self, zinc_ids: List[str]) -> Dict[str, Dict]:
        """Fetch molecular properties from protomers endpoint for a list of ZINC IDs."""
        properties = {}
        for zinc_id in zinc_ids:
            result = self._make_request(
                "protomers.json", {"zinc_id": zinc_id, "count": 5}
            )
            if result["ok"] and result["data"]:
                # Take the first protomer (typically the reference model)
                prot = result["data"][0]
                properties[zinc_id] = {
                    "mwt": prot.get("mwt"),
                    "logp": prot.get("logp"),
                    "hbd": prot.get("hbd"),
                    "hba": prot.get("hba"),
                    "rb": prot.get("rb"),
                    "net_charge": prot.get("net_charge"),
                    "desolv_apol": prot.get("desolv_apol"),
                    "desolv_pol": prot.get("desolv_pol"),
                }
        return properties

    def _search_compounds(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search compounds by name or keyword."""
        query = arguments.get("query")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        count = arguments.get("count", 10)
        purchasability = arguments.get("purchasability")

        params = {"q": query, "count": min(count, 100)}
        if purchasability:
            params["purchasability"] = purchasability

        result = self._make_request("substances/search.json", params)
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        substances = result["data"]
        if not substances:
            return {
                "status": "success",
                "data": [],
                "count": 0,
                "message": "No compounds found matching '{}'".format(query),
            }

        # Enrich with molecular properties for up to 10 compounds
        zinc_ids = [s["zinc_id"] for s in substances[:10]]
        props = self._enrich_with_properties(zinc_ids)

        enriched = []
        for s in substances:
            entry = {
                "zinc_id": s["zinc_id"],
                "smiles": s["smiles"],
            }
            if s["zinc_id"] in props:
                entry.update(props[s["zinc_id"]])
            enriched.append(entry)

        return {
            "status": "success",
            "data": enriched,
            "count": len(enriched),
        }

    def _get_compound(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed compound information including properties and vendors."""
        zinc_id = arguments.get("zinc_id")
        if not zinc_id:
            return {"status": "error", "error": "zinc_id parameter is required"}

        # Normalize ZINC ID format
        zinc_id = zinc_id.strip().upper()
        if not zinc_id.startswith("ZINC"):
            zinc_id = "ZINC" + zinc_id

        # Get basic substance info
        result = self._make_request("substances/{}.json".format(zinc_id))
        if not result["ok"]:
            return {"status": "error", "error": "Compound {} not found".format(zinc_id)}

        substance = result["data"]

        # Get molecular properties from protomers
        props_result = self._make_request(
            "protomers.json", {"zinc_id": zinc_id, "count": 5}
        )
        properties = {}
        if props_result["ok"] and props_result["data"]:
            prot = props_result["data"][0]
            properties = {
                "mwt": prot.get("mwt"),
                "logp": prot.get("logp"),
                "hbd": prot.get("hbd"),
                "hba": prot.get("hba"),
                "rb": prot.get("rb"),
                "net_charge": prot.get("net_charge"),
                "desolv_apol": prot.get("desolv_apol"),
                "desolv_pol": prot.get("desolv_pol"),
            }

        # Get vendor/catalog information
        catalogs_result = self._make_request(
            "substances/{}/catalogs.json".format(zinc_id)
        )
        vendors = []
        if catalogs_result["ok"] and catalogs_result["data"]:
            for cat in catalogs_result["data"]:
                vendors.append(
                    {
                        "catalog_name": cat.get("name"),
                        "short_name": cat.get("short_name"),
                        "purchasability": cat.get("purchasability"),
                        "is_building_block": cat.get("bb", False),
                    }
                )

        compound = {
            "zinc_id": substance.get("zinc_id", zinc_id),
            "smiles": substance.get("smiles"),
        }
        compound.update(properties)
        compound["vendors"] = vendors
        compound["vendor_count"] = len(vendors)

        # Determine best purchasability tier
        purch_tiers = [v["purchasability"] for v in vendors if v.get("purchasability")]
        tier_order = ["In-Stock", "For-Sale", "On-Demand", "Agent", "Annotated"]
        best_tier = None
        for tier in tier_order:
            if tier in purch_tiers:
                best_tier = tier
                break
        compound["best_purchasability"] = best_tier

        return {
            "status": "success",
            "data": compound,
        }

    def _search_by_smiles(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search compounds by SMILES string."""
        smiles = arguments.get("smiles")
        if not smiles:
            return {"status": "error", "error": "smiles parameter is required"}

        count = arguments.get("count", 10)

        # ZINC search.json endpoint accepts SMILES as the query
        params = {"q": smiles, "count": min(count, 100)}
        result = self._make_request("substances/search.json", params)
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        substances = result["data"]
        if not substances:
            return {
                "status": "success",
                "data": [],
                "count": 0,
                "message": "No compounds found matching SMILES",
            }

        # Enrich with properties
        zinc_ids = [s["zinc_id"] for s in substances[:10]]
        props = self._enrich_with_properties(zinc_ids)

        enriched = []
        for s in substances:
            entry = {
                "zinc_id": s["zinc_id"],
                "smiles": s["smiles"],
            }
            if s["zinc_id"] in props:
                entry.update(props[s["zinc_id"]])
            enriched.append(entry)

        return {
            "status": "success",
            "data": enriched,
            "count": len(enriched),
        }

    def _get_purchasable(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Browse purchasable compounds by availability tier."""
        tier = arguments.get("tier", "in-stock")
        count = arguments.get("count", 10)

        valid_tiers = ["in-stock", "for-sale", "on-demand", "agent", "world", "fda"]
        tier_lower = tier.lower()
        if tier_lower not in valid_tiers:
            return {
                "status": "error",
                "error": "Invalid tier '{}'. Valid: {}".format(
                    tier, ", ".join(valid_tiers)
                ),
            }

        # Use substances/subsets endpoint for browsing by purchasability
        result = self._make_request(
            "substances/subsets/{}.json".format(tier_lower),
            {"count": min(count, 100)},
        )
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        substances = result["data"]
        if not substances:
            return {
                "status": "success",
                "data": [],
                "count": 0,
                "message": "No compounds found for tier '{}'".format(tier),
            }

        # Enrich with properties (limit to 10 to avoid slowness)
        zinc_ids = [s["zinc_id"] for s in substances[:10]]
        props = self._enrich_with_properties(zinc_ids)

        enriched = []
        for s in substances:
            entry = {
                "zinc_id": s["zinc_id"],
                "smiles": s["smiles"],
                "tier": tier_lower,
            }
            if s["zinc_id"] in props:
                entry.update(props[s["zinc_id"]])
            enriched.append(entry)

        return {
            "status": "success",
            "data": enriched,
            "count": len(enriched),
            "tier": tier_lower,
        }

    def _search_by_properties(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Filter compounds by molecular properties using protomers endpoint.

        Since ZINC does not support property range filters as query params,
        this fetches a batch of protomers and filters client-side by the
        specified property ranges.
        """
        mwt_min = arguments.get("mwt_min")
        mwt_max = arguments.get("mwt_max")
        logp_min = arguments.get("logp_min")
        logp_max = arguments.get("logp_max")
        hbd_max = arguments.get("hbd_max")
        hba_max = arguments.get("hba_max")
        rb_max = arguments.get("rb_max")
        purchasability = arguments.get("purchasability")
        count = arguments.get("count", 20)

        # Determine base endpoint based on purchasability filter
        if purchasability:
            valid_tiers = ["in-stock", "for-sale", "on-demand", "agent"]
            if purchasability.lower() not in valid_tiers:
                return {
                    "status": "error",
                    "error": "Invalid purchasability '{}'. Valid: {}".format(
                        purchasability, ", ".join(valid_tiers)
                    ),
                }
            endpoint = "protomers/subsets/{}.json".format(purchasability.lower())
        else:
            endpoint = "protomers.json"

        # Fetch a larger batch to filter from (up to 200 to find enough matches)
        fetch_count = min(count * 10, 200)
        result = self._make_request(endpoint, {"count": fetch_count})
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        protomers = result["data"]
        if not protomers:
            return {
                "status": "success",
                "data": [],
                "count": 0,
                "message": "No protomers found to filter",
            }

        # Apply property filters
        filtered = []
        for p in protomers:
            mwt = p.get("mwt")
            logp = p.get("logp")
            hbd = p.get("hbd")
            hba = p.get("hba")
            rb = p.get("rb")

            if mwt_min is not None and (mwt is None or mwt < mwt_min):
                continue
            if mwt_max is not None and (mwt is None or mwt > mwt_max):
                continue
            if logp_min is not None and (logp is None or logp < logp_min):
                continue
            if logp_max is not None and (logp is None or logp > logp_max):
                continue
            if hbd_max is not None and (hbd is None or hbd > hbd_max):
                continue
            if hba_max is not None and (hba is None or hba > hba_max):
                continue
            if rb_max is not None and (rb is None or rb > rb_max):
                continue

            filtered.append(
                {
                    "zinc_id": p.get("zinc_id"),
                    "smiles": p.get("smiles"),
                    "mwt": mwt,
                    "logp": logp,
                    "hbd": hbd,
                    "hba": hba,
                    "rb": rb,
                    "net_charge": p.get("net_charge"),
                }
            )

            if len(filtered) >= count:
                break

        return {
            "status": "success",
            "data": filtered,
            "count": len(filtered),
            "filters_applied": {
                k: v
                for k, v in {
                    "mwt_min": mwt_min,
                    "mwt_max": mwt_max,
                    "logp_min": logp_min,
                    "logp_max": logp_max,
                    "hbd_max": hbd_max,
                    "hba_max": hba_max,
                    "rb_max": rb_max,
                    "purchasability": purchasability,
                }.items()
                if v is not None
            },
        }
