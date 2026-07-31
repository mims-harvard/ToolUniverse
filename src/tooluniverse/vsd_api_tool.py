from __future__ import annotations
import os
import json
from typing import Dict, Any

from .base_tool import BaseTool
from .tool_registry import register_tool

# Reuse same storage locations as vsd_tool
VSD_HOME = os.environ.get("TOOLUNIVERSE_VSD_DIR", os.path.expanduser("~/.tooluniverse/vsd"))
GENERATED_TOOLS_PATH = os.path.join(VSD_HOME, "generated_tools.json")

os.makedirs(VSD_HOME, exist_ok=True)


def _save_tool(tool_spec: Dict[str, Any]) -> None:
    """Upsert a generated tool spec into the registry file."""
    tools: list[Dict[str, Any]] = []
    if os.path.exists(GENERATED_TOOLS_PATH):
        try:
            with open(GENERATED_TOOLS_PATH, "r", encoding="utf-8") as f:
                tools = json.load(f)
        except Exception:
            tools = []
    by_name = {t.get("name"): t for t in tools}
    by_name[tool_spec.get("name")] = tool_spec
    with open(GENERATED_TOOLS_PATH, "w", encoding="utf-8") as f:
        json.dump(list(by_name.values()), f, indent=2)


@register_tool("VSDToolBuilder")
class VSDToolBuilder(BaseTool):
    """
    Build and register a usable ToolUniverse tool from a harvested or discovered VSD candidate.

    Input:
      {
        "candidate": {
          "domain": "clinicaltrials.gov",
          "endpoint": "https://clinicaltrials.gov/api/v2/studies",
          "license": "CC0",
          "score": 0.92
        },
        "tool_name": "clinicaltrials_search",
        "description": "Query clinical trials with disease/condition filters",
        "parameter_overrides": { ... optional JSON Schema ... }
      }

    Output:
      {
        "registered": true,
        "name": "clinicaltrials_search",
        "config_path": "/path/to/generated_tools.json"
      }
    """

    def run(self, arguments: Dict[str, Any]):
        if not arguments:
            return {"error": "Missing arguments"}
        cand = arguments.get("candidate") or {}
        tool_name = arguments.get("tool_name")
        desc = arguments.get("description") or f"VSD tool for {cand.get('domain')}"
        param_override = arguments.get("parameter_overrides") or {}

        if not tool_name:
            return {"error": "tool_name is required"}
        if not cand or not cand.get("endpoint"):
            return {"error": "candidate with endpoint is required"}

        endpoint = cand.get("endpoint")
        domain = cand.get("domain", "unknown")

        # Pick implementation type
        if endpoint.endswith(".graphql") or "graphql" in endpoint:
            impl_type = "GenericGraphQLTool"
        elif endpoint.startswith("http"):
            impl_type = "GenericRESTTool"
        else:
            impl_type = "URLHTMLTagTool"

        # Default parameter schema (can be overridden)
        params = param_override or {
            "type": "object",
            "properties": {
                "query": {"type": "string", "default": ""},
                "pageSize": {"type": "integer", "default": 10},
            }
        }

        tool_spec = {
            "type": impl_type,
            "name": tool_name,
            "description": desc,
            "fields": {
                "base_url": endpoint,
                "method": "GET",
                "default_params": {}
            },
            "parameter": params,
            "label": ["VSD", cand.get("label") or domain],
            "vsd": {
                "domain": domain,
                "endpoint": endpoint,
                "license": cand.get("license", "unknown"),
                "score": cand.get("score"),
                "registry": cand.get("registry", "catalog"),
            }
        }

        # Special case: ClinicalTrials.gov -> add arg_transform
        if "clinicaltrials.gov" in endpoint and impl_type == "GenericRESTTool":
            tool_spec["vsd"]["arg_transform"] = "ctgov_time_window"

        _save_tool(tool_spec)
        return {"registered": True, "name": tool_name, "config_path": GENERATED_TOOLS_PATH}
