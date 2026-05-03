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


@register_tool(
    "AOPWikiListTool",
    config={
        "name": "AOPWiki_list_aops",
        "type": "AOPWikiListTool",
        "description": (
            "List Adverse Outcome Pathways (AOPs) from AOPWiki. Returns AOP IDs, "
            "titles, and short names. AOPs describe causal chains from molecular "
            "initiating events through key events to adverse outcomes, used in "
            "toxicology and risk assessment."
        ),
        "parameter": {
            "type": "object",
            "properties": {},
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

        try:
            result = _get_json(f"{base}/aops.json", timeout=timeout)
        except Exception as e:
            return {"status": "error", "error": f"AOPWiki API error: {e}"}

        if not isinstance(result, list):
            return {"status": "error", "error": "Unexpected response format"}

        aops = []
        for item in result:
            aops.append(
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "short_name": item.get("short_name"),
                }
            )

        return {
            "status": "success",
            "data": aops,
        }


@register_tool(
    "AOPWikiDetailTool",
    config={
        "name": "AOPWiki_get_aop",
        "type": "AOPWikiDetailTool",
        "description": (
            "Get detailed information about a specific Adverse Outcome Pathway "
            "(AOP) from AOPWiki by AOP ID. Returns the molecular initiating "
            "events (MIEs), key events (KEs), adverse outcomes (AOs), stressors "
            "(chemicals), and key event relationships (causal chain)."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "aop_id": {
                    "type": "integer",
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
        aop_id = arguments.get("aop_id")
        if aop_id is None:
            return {"status": "error", "error": "aop_id is required"}

        base = self.tool_config.get("settings", {}).get("base_url", _BASE)
        timeout = int(self.tool_config.get("settings", {}).get("timeout", 30))

        try:
            result = _get_json(f"{base}/aops/{aop_id}.json", timeout=timeout)
        except Exception as e:
            return {"status": "error", "error": f"AOPWiki API error: {e}"}

        if isinstance(result, dict) and result.get("status") in (404, 500):
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
                {"event_id": e.get("event_id"), "event": e.get("event")}
                for e in result.get("aop_mies", [])
            ],
            "key_events": [
                {"event_id": e.get("event_id"), "event": e.get("event")}
                for e in result.get("aop_kes", [])
            ],
            "adverse_outcomes": [
                {"event_id": e.get("event_id"), "event": e.get("event")}
                for e in result.get("aop_aos", [])
            ],
            "relationships": [
                {
                    "upstream_event_id": r.get("upstream_event_id"),
                    "upstream_event": r.get("upstream_event"),
                    "downstream_event_id": r.get("downstream_event_id"),
                    "downstream_event": r.get("downstream_event"),
                }
                for r in result.get("relationships", [])
            ],
        }

        return {"status": "success", "data": data}
