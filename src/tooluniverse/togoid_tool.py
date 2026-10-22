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
        if not isinstance(arguments, dict):
            return {"status": "error", "error": "arguments must be an object"}
        unknown = sorted(set(arguments) - {"ids", "source", "target"})
        if unknown:
            return {
                "status": "error",
                "error": f"Unsupported parameter(s): {', '.join(unknown)}",
            }
        ids = arguments.get("ids")
        source = arguments.get("source")
        target = arguments.get("target")
        if not all(
            isinstance(value, str) and value.strip() for value in (ids, source, target)
        ):
            return {
                "status": "error",
                "error": "'ids', 'source', and 'target' are required (source/target are "
                "TogoID dataset names — call TogoID_list_datasets for valid names).",
            }
        ids = ids.strip()
        source = source.strip()
        target = target.strip()
        input_ids = [identifier.strip() for identifier in ids.split(",")]
        if any(not identifier for identifier in input_ids):
            return {
                "status": "error",
                "error": "ids must not contain empty comma-separated values",
            }
        if len(input_ids) > 50:
            return {
                "status": "error",
                "error": "At most 50 input identifiers are allowed per call",
            }
        if len(set(input_ids)) != len(input_ids):
            return {
                "status": "error",
                "error": "ids must not contain duplicate identifiers",
            }
        if any(
            not character.isalnum() and character != "_"
            for character in source + target
        ):
            return {
                "status": "error",
                "error": "source and target must be TogoID dataset names",
            }

        mappings = []
        converted_union = []
        converted_seen = set()
        unmapped_ids = []
        for input_id in input_ids:
            params = {
                "ids": input_id,
                "route": f"{source},{target}",
                "format": "json",
            }
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
            if (
                not isinstance(payload, dict)
                or payload.get("ids") != [input_id]
                or payload.get("route") != [source, target]
                or not isinstance(payload.get("results"), list)
                or any(not isinstance(result, str) for result in payload["results"])
            ):
                return {
                    "status": "error",
                    "error": f"TogoID returned malformed or mismatched data for input {input_id}",
                }

            converted_ids = payload["results"]
            if not converted_ids:
                unmapped_ids.append(input_id)
            mappings.append(
                {
                    "input_id": input_id,
                    "converted_ids": converted_ids,
                    "converted_count": len(converted_ids),
                    "mapped": bool(converted_ids),
                }
            )
            for converted_id in converted_ids:
                if converted_id not in converted_seen:
                    converted_seen.add(converted_id)
                    converted_union.append(converted_id)

        return {
            "status": "success",
            "data": {
                "input_ids": input_ids,
                "source": source,
                "target": target,
                "mappings": mappings,
                "converted_ids": converted_union,
                "unmapped_ids": unmapped_ids,
                "input_count": len(input_ids),
                "mapped_input_count": len(input_ids) - len(unmapped_ids),
                "all_inputs_mapped": not unmapped_ids,
                "total_associations": sum(
                    mapping["converted_count"] for mapping in mappings
                ),
            },
            "metadata": {
                "returned": len(converted_union),
                "mapping_complete": True,
                "request_count": len(input_ids),
                "note": "mappings preserves each input-to-output association; converted_ids is a compatibility union of unique targets",
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
        if not isinstance(arguments, dict):
            return {"status": "error", "error": "arguments must be an object"}
        unknown = sorted(set(arguments) - {"category"})
        if unknown:
            return {
                "status": "error",
                "error": f"Unsupported parameter(s): {', '.join(unknown)}",
            }
        category_value = arguments.get("category")
        if category_value is not None and (
            not isinstance(category_value, str) or not category_value.strip()
        ):
            return {
                "status": "error",
                "error": "category must be a non-empty string when provided",
            }
        category = category_value.strip().lower() if category_value else ""
        cfg, error = _togoid_get("/config/dataset", self.timeout)
        if error:
            return error

        if not isinstance(cfg, dict):
            return {
                "status": "error",
                "error": "Unexpected TogoID dataset config format",
            }
        if any(
            not isinstance(key, str)
            or not isinstance(meta, dict)
            or not isinstance(meta.get("label"), str)
            or not isinstance(meta.get("category"), str)
            for key, meta in cfg.items()
        ):
            return {
                "status": "error",
                "error": "TogoID returned malformed dataset metadata",
            }
        available_categories = sorted({meta["category"] for meta in cfg.values()})
        matched_category = next(
            (value for value in available_categories if value.lower() == category), None
        )
        if category and matched_category is None:
            return {
                "status": "error",
                "error": f"Unknown TogoID category: {category_value}",
                "available_categories": available_categories,
            }
        datasets = []
        for key, meta in cfg.items():
            if matched_category and meta["category"] != matched_category:
                continue
            datasets.append(
                {
                    "dataset": key,
                    "label": meta["label"],
                    "category": meta["category"],
                    "catalog": meta.get("catalog"),
                    "regex": meta.get("regex"),
                    "annotations": meta.get("annotations", []),
                    "examples": meta.get("examples", []),
                    "prefixes": meta.get("prefix", []),
                    "record": meta,
                }
            )
        datasets.sort(key=lambda d: (d["category"] or "", d["dataset"]))
        return {
            "status": "success",
            "data": datasets,
            "metadata": {
                "total": len(datasets),
                "total_available": len(cfg),
                "category_filter": matched_category,
                "available_categories": available_categories,
                "result_set_complete": True,
                "source_records_complete": True,
                "source": "TogoID (DBCLS)",
            },
        }
