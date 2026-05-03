"""
PROTAC-DB 3.0 Tool

Provides access to PROTAC-DB 3.0 (https://cadd.zju.edu.cn/protacdb/) for querying
PROTAC (Proteolysis Targeting Chimera) compound data, including structures, targets,
E3 ligases, DC50 values, and degradation data.

API: https://cadd.zju.edu.cn/protacdb/
No authentication required. Uses Tornado CSRF session cookies.
"""

import requests
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool
from .tool_registry import register_tool

PROTACDB_BASE_URL = "https://cadd.zju.edu.cn/protacdb"

# Property filter fields required by the compound search endpoint
_PROPERTY_FILTERS = [
    "molwt_min",
    "molwt_max",
    "heavyatomcount_min",
    "heavyatomcount_max",
    "ringcount_min",
    "ringcount_max",
    "xlogp3_min",
    "xlogp3_max",
    "numhacceptors_min",
    "numhacceptors_max",
    "numhdonors_min",
    "numhdonors_max",
    "numrotatablebonds_min",
    "numrotatablebonds_max",
    "tpsa_min",
    "tpsa_max",
]


@register_tool("ProtacDBTool")
class ProtacDBTool(BaseTool):
    """
    Tool for querying PROTAC-DB 3.0 (Zhejiang University).

    Provides access to:
    - PROTAC compound search and retrieval by target or E3 ligase
    - Compound details (SMILES, DC50, Dmax, cell lines, references)
    - Target protein information
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def _get_session_with_xsrf(self):
        session = requests.Session()
        session.get(f"{PROTACDB_BASE_URL}/", timeout=30)
        return session

    def _build_files(
        self, session: requests.Session, extra: Optional[Dict] = None
    ) -> Dict:
        xsrf = session.cookies.get("_xsrf", "")
        files: Dict = {"_xsrf": (None, xsrf)}
        for f in _PROPERTY_FILTERS:
            files[f] = (None, "none")
        if extra:
            files.update({k: (None, str(v)) for k, v in extra.items()})
        return files

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        operation_handlers = {
            "search_protacs": self._search_protacs,
            "get_protac": self._get_protac,
            "search_targets": self._search_targets,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}",
                "available_operations": list(operation_handlers.keys()),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "PROTAC-DB API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to PROTAC-DB API"}
        except Exception as e:
            return {"status": "error", "error": f"Operation failed: {str(e)}"}

    def _search_protacs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        target = arguments.get("target")
        e3_ligase = arguments.get("e3_ligase")
        max_results = int(arguments.get("max_results", 50))

        if not target and not e3_ligase:
            return {
                "status": "error",
                "error": "At least one of 'target' or 'e3_ligase' is required",
            }

        session = self._get_session_with_xsrf()

        if target:
            # Build search URL: path-params format used by PROTAC-DB
            path = (
                f"search/target={requests.utils.quote(target, safe='')}&dataset=protac"
            )
            if e3_ligase:
                path += f"&e3={requests.utils.quote(e3_ligase, safe='')}"
            url = f"{PROTACDB_BASE_URL}/{path}"
        else:
            # E3-only: browse all compounds, filter client-side
            url = f"{PROTACDB_BASE_URL}/browse/compound?dataset=protac"

        files = self._build_files(
            session,
            {
                "page": "1",
                "rows": str(min(max_results, 100)),
                "column_name": "none",
                "sort_way": "none",
            },
        )

        resp = session.post(url, files=files, timeout=60)
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"PROTAC-DB API returned status {resp.status_code}",
                "detail": resp.text[:300],
            }

        try:
            data = resp.json()
        except Exception:
            return {
                "status": "error",
                "error": "Failed to parse PROTAC-DB response as JSON",
            }

        if not isinstance(data, list) or not data:
            return {
                "status": "error",
                "error": "Unexpected response format from PROTAC-DB",
            }

        # Last element is metadata
        meta = data[-1] if isinstance(data[-1], dict) and "total" in data[-1] else {}
        compounds: List[Dict] = [item for item in data[:-1] if isinstance(item, dict)]

        # Client-side E3 filter for browse-all mode
        if not target and e3_ligase:
            compounds = [
                c
                for c in compounds
                if e3_ligase.upper() in str(c.get("e3_ligase", "")).upper()
            ]

        return {
            "status": "success",
            "data": compounds,
            "num_results": len(compounds),
            "total_in_db": meta.get("total"),
        }

    def _get_protac(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        protac_id = arguments.get("protac_id")
        if not protac_id:
            return {"status": "error", "error": "protac_id is required"}

        session = self._get_session_with_xsrf()
        xsrf = session.cookies.get("_xsrf", "")

        url = f"{PROTACDB_BASE_URL}/compound/dataset=protac&id={protac_id}"
        resp = session.post(url, files={"_xsrf": (None, xsrf)}, timeout=30)

        if resp.status_code == 200:
            try:
                return {"status": "success", "data": resp.json()}
            except Exception:
                return {
                    "status": "error",
                    "error": "Failed to parse PROTAC-DB compound response",
                }
        elif resp.status_code == 404:
            return {
                "status": "error",
                "error": f"PROTAC compound ID {protac_id} not found",
            }
        else:
            return {
                "status": "error",
                "error": f"API request failed with status {resp.status_code}",
                "detail": resp.text[:300],
            }

    def _search_targets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        target_name = arguments.get("target_name")
        uniprot_id = arguments.get("uniprot_id")

        session = self._get_session_with_xsrf()
        xsrf = session.cookies.get("_xsrf", "")

        url = f"{PROTACDB_BASE_URL}/browse/target"
        resp = session.post(
            url,
            files={"_xsrf": (None, xsrf), "dataset": (None, "protac")},
            timeout=30,
        )

        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"PROTAC-DB target API returned status {resp.status_code}",
            }

        try:
            all_targets = resp.json()
        except Exception:
            return {
                "status": "error",
                "error": "Failed to parse PROTAC-DB target response",
            }

        if not isinstance(all_targets, list):
            return {"status": "error", "error": "Unexpected format for target list"}

        # Client-side filtering
        if target_name:
            filtered = [
                t
                for t in all_targets
                if target_name.upper() in str(t.get("short_target_name", "")).upper()
                or target_name.upper() in str(t.get("long_target_name", "")).upper()
                or target_name.upper() in str(t.get("short_target_name_2", "")).upper()
                or target_name.upper() in str(t.get("short_target_name_3", "")).upper()
            ]
        elif uniprot_id:
            filtered = [
                t
                for t in all_targets
                if uniprot_id.upper() in str(t.get("uniprot_id", "")).upper()
            ]
        else:
            filtered = all_targets

        return {
            "status": "success",
            "data": filtered,
            "num_results": len(filtered),
        }
