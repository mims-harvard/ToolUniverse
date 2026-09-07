# molgluedb_tool.py
"""
MolGlueDB tools for ToolUniverse -- molecular glue degrader compounds.

MolGlueDB (molgluedb.com) is a curated database of molecular glue
degraders (MGDs): small molecules that induce proximity between a target
protein and a recruiting protein (e.g. an E3 ligase) without the
warhead-linker-ligand architecture of a PROTAC. ToolUniverse's existing
PROTAC-DB tools (protacdb_tool.py) cover that other, bifunctional
degrader modality; MolGlueDB fills the monofunctional-glue gap, with
structural, degradation, and physicochemical data plus curated
pharmacophore/scaffold classifications (e.g. "Glutarimide" /
"LenalidomideType") that PROTAC-DB has no equivalent for.

There is no documented public API, but the site's own frontend calls a
same-origin JSON backend at /api/query_bj_data (search) and
/api/query_bj_data_by_id (single record). That backend sits behind a
WAF that silently serves the SPA shell (HTTP 200, no error) to requests
lacking a browser-like User-Agent and Referer -- both are set here for
that reason, not to evade any access control (the data itself is fully
public and described by its publisher as free and open-access).

No authentication required.
"""

from typing import Any, Dict, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

MOLGLUEDB_BASE_URL = "https://www.molgluedb.com/api"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ToolUniverse/1.0)",
    "Referer": "https://www.molgluedb.com/",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

_FIELDS = (
    "id",
    "Name",
    "SMILES",
    "IUPAC",
    "StdInChIKey",
    "Formula",
    "MolWeight",
    "Pharmacophore",
    "Core",
    "ModeOfAction",
    "ResearchStage",
    "PrimaryTarget",
    "PrimaryTargetDegInfo",
    "SecondaryTarget",
    "SecondaryTargetDegInfo",
    "RecruitingProtein",
    "RecruitingProtein_UniProtID",
    "PDB",
    "SourceName",
    "SourceAddress_Website",
)


def _summarize(rec: Dict[str, Any]) -> Dict[str, Any]:
    return {field: rec.get(field) for field in _FIELDS}


@register_tool("MolGlueDBTool")
class MolGlueDBTool(BaseTool):
    """
    Tool for querying MolGlueDB, dispatched by fields.operation:
      - "search_compounds" : full-text keyword search over molecular glues
      - "get_compound"     : a single compound by its MolGlueDB id

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_compounds"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if self.operation == "search_compounds":
                return self._search_compounds(arguments)
            if self.operation == "get_compound":
                return self._get_compound(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"MolGlueDB request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"MolGlueDB request failed: {e}"}
        except ValueError:
            return {
                "status": "error",
                "error": "MolGlueDB returned a non-JSON response",
            }

    def _limit(self, arguments: Dict[str, Any], default: int = 30) -> int:
        try:
            return max(1, min(int(arguments.get("limit") or default), 200))
        except (TypeError, ValueError):
            return default

    def _search_compounds(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        keyword = (arguments.get("keyword") or "").strip()
        if not keyword:
            return {
                "status": "error",
                "error": "keyword is required, e.g. a target protein "
                "('IKZF2'), recruiting protein ('CRBN'), or compound name "
                "('Lenalidomide').",
            }

        limit = self._limit(arguments)
        resp = requests.post(
            f"{MOLGLUEDB_BASE_URL}/query_bj_data",
            json={"page": 1, "pageSize": limit, "keyword": keyword},
            headers=_HEADERS,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("status") != "success":
            return {
                "status": "error",
                "error": f"MolGlueDB search failed: {payload}",
            }

        rows = payload.get("data") or []
        return {
            "status": "success",
            "data": [_summarize(r) for r in rows],
            "metadata": {
                "keyword": keyword,
                "total_matching": payload.get("total"),
                "returned": len(rows),
                "source": "MolGlueDB (molgluedb.com)",
            },
        }

    def _get_compound(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        compound_id = arguments.get("compound_id")
        try:
            compound_id = int(compound_id)
        except (TypeError, ValueError):
            return {
                "status": "error",
                "error": "compound_id is required and must be an integer, "
                "e.g. 1.",
            }

        resp = requests.get(
            f"{MOLGLUEDB_BASE_URL}/query_bj_data_by_id",
            params={"id": compound_id},
            headers=_HEADERS,
            timeout=self.timeout,
        )
        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"No MolGlueDB compound found for id {compound_id}.",
            }
        resp.raise_for_status()
        payload = resp.json()
        record = payload.get("data")
        if not record:
            return {
                "status": "error",
                "error": f"No MolGlueDB compound found for id {compound_id}.",
            }

        return {
            "status": "success",
            "data": _summarize(record),
            "metadata": {
                "compound_id": compound_id,
                "source": "MolGlueDB (molgluedb.com)",
            },
        }
