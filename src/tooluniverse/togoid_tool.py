"""
TogoID tools for ToolUniverse — universal biological identifier conversion.

TogoID (DBCLS) converts identifiers between 117 biological databases across genes,
proteins, transcripts, compounds, diseases, pathways, variants, cell lines, organisms,
and more — using a curated relation graph. These tools convert IDs and list the
supported ID types. Complements the translate-id workflow with a single broad resolver.

API: https://api.togoid.dbcls.jp  (public, no authentication, JSON)
  - GET /convert?ids=...&route=<source>,<target>
  - GET /config/dataset   (the 117 supported ID datasets)
Conversion uses DIRECT relations: source and target must be adjacent in the graph
(e.g. ensembl_gene<->uniprot works; ncbigene<->chebi returns "no route").
"""

from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

TOGOID_BASE = "https://api.togoid.dbcls.jp"


def _togoid_get(path: str, timeout: int, params: Dict[str, Any] | None = None):
    """GET a TogoID endpoint and return (payload, None) or (None, error_dict)."""
    try:
        resp = requests.get(
            f"{TOGOID_BASE}{path}",
            params=params,
            headers={"Accept": "application/json"},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.Timeout:
        return None, {
            "status": "error",
            "error": f"TogoID request timed out after {timeout}s",
        }
    except requests.exceptions.RequestException as e:
        return None, {"status": "error", "error": f"TogoID request failed: {e}"}
    except ValueError:
        return None, {"status": "error", "error": "TogoID returned a non-JSON response"}


@register_tool("TogoIDConvertTool")
class TogoIDConvertTool(BaseTool):
    """Convert identifiers between two directly-related biological databases."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ids = (arguments.get("ids") or "").strip()
        source = (arguments.get("source") or "").strip()
        target = (arguments.get("target") or "").strip()
        if not (ids and source and target):
            return {
                "status": "error",
                "error": "'ids', 'source', and 'target' are required (source/target are "
                "TogoID dataset names — call TogoID_list_datasets for valid names).",
            }

        params = {"ids": ids, "route": f"{source},{target}", "format": "json"}
        payload, error = _togoid_get("/convert", self.timeout, params=params)
        if error:
            return error

        # Unrelated source/target pairs return a {"message": "no route: ..."} body.
        if isinstance(payload, dict) and payload.get("message"):
            return {
                "status": "error",
                "error": f"TogoID: {payload['message']}. source and target must be directly "
                "related; pick adjacent dataset types or convert via an intermediate.",
            }

        results = payload.get("results", []) if isinstance(payload, dict) else []
        return {
            "status": "success",
            "data": {
                "input_ids": payload.get("ids", [])
                if isinstance(payload, dict)
                else [],
                "source": source,
                "target": target,
                "converted_ids": results,
            },
            "metadata": {
                "returned": len(results),
                "note": "converted_ids is the union of target IDs across all inputs",
                "source": "TogoID (DBCLS)",
            },
        }


@register_tool("TogoIDDatasetsTool")
class TogoIDDatasetsTool(BaseTool):
    """List the biological ID datasets TogoID can convert between (optionally by category)."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        category = (arguments.get("category") or "").strip().lower()
        cfg, error = _togoid_get("/config/dataset", self.timeout)
        if error:
            return error

        if not isinstance(cfg, dict):
            return {
                "status": "error",
                "error": "Unexpected TogoID dataset config format",
            }
        datasets = [
            {
                "dataset": key,
                "label": meta.get("label"),
                "category": meta.get("category"),
            }
            for key, meta in cfg.items()
            if isinstance(meta, dict)
            and (not category or (meta.get("category") or "").lower() == category)
        ]
        datasets.sort(key=lambda d: (d["category"] or "", d["dataset"]))
        return {
            "status": "success",
            "data": datasets,
            "metadata": {
                "total": len(datasets),
                "category_filter": category or None,
                "source": "TogoID (DBCLS)",
            },
        }
