"""AOPWiki API tools for Adverse Outcome Pathways.

AOPWiki provides structured data on Adverse Outcome Pathways (AOPs) that
link molecular initiating events through key events to adverse outcomes.
Used in toxicology and regulatory science.
"""

import json
from typing import Any, Dict
from urllib.request import Request, urlopen

from tooluniverse.tool_registry import register_tool

_BASE = "https://aopwiki.org"


def _get_json(url: str, timeout: int = 30) -> Any:
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def _aopwiki_not_found(result: Any) -> bool:
    """AOP-Wiki returns HTTP 200 with a body like
    {"message": "This AOP does not exist.", "status": "unprocessable_entity"}
    for an invalid id (confirmed live for both /aops and /events) -- there is
    no HTTP error to catch. Detect that string status, not a numeric one.
    """
    return isinstance(result, dict) and result.get("status") in (
        404,
        500,
        "unprocessable_entity",
    )


@register_tool(
    "AOPWikiListTool",
    config={
        "name": "AOPWiki_list_aops",
        "type": "AOPWikiListTool",
        "description": (
            "List the complete AOP-Wiki catalog after verifying stable page totals "
            "and non-overlapping IDs. Optional search filters the verified complete "
            "catalog by title or short name."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "search": {
                    "type": "string",
                    "description": (
                        "Case-insensitive keyword to filter AOPs by title or short "
                        "name. Omit to return every AOP."
                    ),
                },
            },
        },
        "settings": {"base_url": _BASE, "timeout": 30},
    },
)
class AOPWikiListTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        base = self.tool_config.get("settings", {}).get("base_url", _BASE)
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        search_argument = arguments.get("search")
        if search_argument is not None and not isinstance(search_argument, str):
            return {"status": "error", "error": "search must be a string"}

        aops, page = [], 1
        expected_total = None
        expected_pages = None
        seen_ids = set()
        try:
            while True:
                payload = _get_json(
                    f"{base}/aops.json?per_page=500&page={page}", timeout=timeout
                )
                if not isinstance(payload, dict):
                    return {
                        "status": "error",
                        "error": "AOPWiki list response omitted pagination metadata; completeness cannot be verified",
                    }
                items = payload.get("aops")
                if not isinstance(items, list):
                    return {"status": "error", "error": "Unexpected response format"}
                pagination = payload.get("pagination")
                if not isinstance(pagination, dict):
                    return {
                        "status": "error",
                        "error": "AOPWiki list response omitted pagination metadata; completeness cannot be verified",
                    }
                current_page = pagination.get("current_page")
                total_entries = pagination.get("total_entries")
                total_pages = pagination.get("total_pages")
                if (
                    isinstance(current_page, bool)
                    or not isinstance(current_page, int)
                    or current_page != page
                    or isinstance(total_entries, bool)
                    or not isinstance(total_entries, int)
                    or total_entries < 0
                    or isinstance(total_pages, bool)
                    or not isinstance(total_pages, int)
                    or total_pages < 1
                ):
                    return {
                        "status": "error",
                        "error": "AOPWiki returned invalid or conflicting pagination metadata",
                    }
                if expected_total is None:
                    expected_total = total_entries
                    expected_pages = total_pages
                elif total_entries != expected_total or total_pages != expected_pages:
                    return {
                        "status": "error",
                        "error": "AOPWiki pagination totals changed while pages were being retrieved",
                    }

                page_items = [
                    {
                        "id": it.get("id"),
                        "title": it.get("title"),
                        "short_name": it.get("short_name"),
                    }
                    for it in items
                    if isinstance(it, dict)
                ]
                page_ids = [item["id"] for item in page_items]
                if len(set(page_ids)) != len(page_ids) or any(
                    item_id in seen_ids for item_id in page_ids
                ):
                    return {
                        "status": "error",
                        "error": "AOPWiki pagination repeated an AOP across pages",
                    }
                seen_ids.update(page_ids)
                aops.extend(page_items)
                if page >= total_pages:
                    break
                page += 1
        except Exception as e:
            return {"status": "error", "error": f"AOPWiki API error: {e}"}

        if len(aops) != expected_total:
            return {
                "status": "error",
                "error": (
                    f"AOPWiki reported {expected_total} AOPs but returned {len(aops)}; "
                    "result set is incomplete"
                ),
            }

        metadata = {
            "total_aops": expected_total,
            "total_aops_is_exact": True,
            "pages_fetched": expected_pages,
            "result_set_complete": True,
        }

        # AOPWiki's /aops.json has no server-side keyword filter, so filter the
        # fetched list here rather than making callers pull ~600 AOPs and grep.
        search = (search_argument or "").strip().lower()
        if not search:
            return {
                "status": "success",
                "data": aops,
                "count": len(aops),
                "total_aops": expected_total,
                "metadata": metadata,
            }

        matches = [
            a
            for a in aops
            if search in str(a.get("title") or "").lower()
            or search in str(a.get("short_name") or "").lower()
        ]
        result = {
            "status": "success",
            "data": matches,
            "count": len(matches),
            "total_aops": len(aops),
            "search": arguments.get("search"),
            "metadata": metadata,
        }
        if not matches:
            result["note"] = (
                f"No AOP title or short name contains '{arguments.get('search')}'. "
                f"Searched all {len(aops)} AOPs. Try a broader keyword (AOPWiki "
                "titles use terms like 'thyroid', 'PPAR', 'steatosis', "
                "'neurotoxicity'), or omit `search` to list every AOP."
            )
        return result


@register_tool(
    "AOPWikiDetailTool",
    config={
        "name": "AOPWiki_get_aop",
        "type": "AOPWikiDetailTool",
        "description": (
            "Get one AOP with stressors, typed events, and directed event pairs. "
            "The source relation number is an opaque AOP association reference, "
            "not a safe /relationships/{id} identifier."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "aop_id": {
                    "type": "integer",
                    "minimum": 1,
                    "description": (
                        "AOP numeric identifier. Find IDs using AOPWiki_list_aops. "
                        "Example: 3 (mitochondrial complex I inhibition leading to "
                        "parkinsonian motor deficits)."
                    ),
                },
            },
            "required": ["aop_id"],
        },
        "settings": {"base_url": _BASE, "timeout": 30},
    },
)
class AOPWikiDetailTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        settings = self.tool_config.get("settings", {})
        base = settings.get("base_url", _BASE)
        timeout = int(settings.get("timeout", 30))

        # A config can set settings.endpoint_kind = "event" to fetch a single
        # AOP-Wiki Key Event (/events/{id}.json) with its ontology-annotated
        # event_components, instead of the default whole-AOP detail.
        if settings.get("endpoint_kind") == "event":
            return self._run_event(arguments, base, timeout)
        return self._run_aop(arguments, base, timeout)

    def _run_event(
        self, arguments: Dict[str, Any], base: str, timeout: int
    ) -> Dict[str, Any]:
        event_id = arguments.get("event_id")
        if event_id is None:
            return {"status": "error", "error": "event_id is required"}
        if isinstance(event_id, bool) or not isinstance(event_id, int) or event_id <= 0:
            return {"status": "error", "error": "event_id must be a positive integer"}

        try:
            result = _get_json(f"{base}/events/{event_id}.json", timeout=timeout)
        except Exception as e:
            return {"status": "error", "error": f"AOPWiki API error: {e}"}

        if not isinstance(result, dict) or _aopwiki_not_found(result):
            return {
                "status": "error",
                "error": f"Key Event {event_id} not found or server error",
            }

        def _term(node):
            if not isinstance(node, dict):
                return None
            return {"term": node.get("term"), "source_id": node.get("source_id")}

        components = []
        for comp in result.get("event_components", []) or []:
            if not isinstance(comp, dict):
                continue
            components.append(
                {
                    "id": comp.get("id"),
                    "process": _term(comp.get("process")),
                    "object": _term(comp.get("object")),
                    "action": _term(comp.get("action")),
                }
            )

        data = {
            "id": result.get("id"),
            "title": result.get("title"),
            "short_name": result.get("short_name"),
            "biological_organization": result.get("biological_organization"),
            "created_at": result.get("created_at"),
            "updated_at": result.get("updated_at"),
            "event_components": components,
        }
        return {"status": "success", "data": data}

    def _run_aop(
        self, arguments: Dict[str, Any], base: str, timeout: int
    ) -> Dict[str, Any]:
        aop_id = arguments.get("aop_id")
        if aop_id is None:
            return {"status": "error", "error": "aop_id is required"}
        if isinstance(aop_id, bool) or not isinstance(aop_id, int) or aop_id <= 0:
            return {"status": "error", "error": "aop_id must be a positive integer"}

        try:
            result = _get_json(f"{base}/aops/{aop_id}.json", timeout=timeout)
        except Exception as e:
            return {"status": "error", "error": f"AOPWiki API error: {e}"}

        if _aopwiki_not_found(result):
            return {
                "status": "error",
                "error": f"AOP {aop_id} not found or server error",
            }

        data = {
            "id": result.get("id"),
            "title": result.get("title"),
            "short_name": result.get("short_name"),
            "created_at": result.get("created_at"),
            "updated_at": result.get("updated_at"),
            "stressors": [
                {"id": s.get("stressor_id"), "name": s.get("stressor_name")}
                for s in result.get("aop_stressors", [])
            ],
            "molecular_initiating_events": [
                {
                    "event_id": e.get("event_id"),
                    "event": e.get("event"),
                    "event_type": e.get("event_type"),
                }
                for e in result.get("aop_mies", [])
            ],
            "key_events": [
                {
                    "event_id": e.get("event_id"),
                    "event": e.get("event"),
                    "event_type": e.get("event_type"),
                }
                for e in result.get("aop_kes", [])
            ],
            "adverse_outcomes": [
                {
                    "event_id": e.get("event_id"),
                    "event": e.get("event"),
                    "event_type": e.get("event_type"),
                }
                for e in result.get("aop_aos", [])
            ],
            "relationships": [
                {
                    "source_relation": r.get("relation"),
                    "source_relation_semantics": "opaque_aop_association_reference",
                    "upstream_event_id": r.get("upstream_event_id"),
                    "upstream_event": r.get("upstream_event"),
                    "downstream_event_id": r.get("downstream_event_id"),
                    "downstream_event": r.get("downstream_event"),
                }
                for r in result.get("relationships", [])
            ],
        }

        return {
            "status": "success",
            "data": data,
            "metadata": {
                "source_relation_values_safe_as_relationship_ids": False,
                "source_relation_warning": (
                    "AOP payload relation values are opaque association references. "
                    "Do not use them as /relationships/{id}; live AOPWiki responses "
                    "can resolve the same number to an unrelated event pair."
                ),
            },
        }
