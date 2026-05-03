from tooluniverse.base_tool import BaseTool
from tooluniverse.tool_registry import register_tool

_TIPS = {
    "loading": [
        "Load all tools: tu.load_tools()",
        "Load specific categories: tu.load_tools(tool_type=['uniprot', 'chembl'])",
        "Load specific tools: tu.load_tools(include_tools=['UniProt_get_entry_by_accession'])",
        "Exclude categories: tu.load_tools(exclude_categories=['mcp_auto_loader'])",
        "Exclude tools: tu.load_tools(exclude_tools=['slow_tool'])",
    ],
    "searching": [
        "Keyword search: tu.run({'name': 'Tool_Finder_Keyword', 'arguments': {'description': 'protein search', 'limit': 5}})",
        "List all names: tu.list_built_in_tools(mode='list_name')",
        "List by category: tu.list_built_in_tools(mode='config')",
        "Get tool spec: tu.tool_specification('UniProt_get_entry_by_accession')",
        "CLI grep: tu grep protein",
    ],
    "running": [
        "Run a tool: tu.run({'name': 'ToolName', 'arguments': {'param': 'value'}})",
        "run() always returns a dict and never raises exceptions",
        "Check for errors: if 'error' in result: handle_error(result['error'])",
        "Use caching: tu.run({...}, use_cache=True)",
        'CLI run: tu run UniProt_get_entry_by_accession \'{"accession": "P05067"}\'',
    ],
    "workspace": [
        "Workspace dir: .tooluniverse/ in the current directory",
        "Profile config: .tooluniverse/profile.yaml — loaded automatically at startup",
        "API keys: .tooluniverse/.env (never commit this file)",
        "Override workspace: ToolUniverse(workspace='/path/to/workspace')",
        "Global workspace: tu serve --global",
    ],
}

_ALL_TOPICS = sorted(_TIPS.keys())


@register_tool(
    "UsageTipsTool",
    config={
        "name": "ToolUniverse_get_usage_tips",
        "type": "UsageTipsTool",
        "category": "special_tools",
        "description": (
            "Return concise usage tips for the ToolUniverse SDK. "
            "Use topic='all' (default) to get all tips, or specify a topic: "
            + ", ".join(f"'{t}'" for t in _ALL_TOPICS)
            + ". No API keys or network access required — always available offline."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": (
                        "Topic to filter tips. One of: "
                        + ", ".join(f"'{t}'" for t in _ALL_TOPICS)
                        + ", or 'all' (default) to return every topic."
                    ),
                    "enum": _ALL_TOPICS + ["all"],
                    "default": "all",
                    "required": False,
                }
            },
            "required": [],
        },
    },
)
class UsageTipsTool(BaseTool):
    def run(self, arguments):
        topic = (arguments or {}).get("topic", "all")
        if topic == "all" or topic is None:
            return {"topic": "all", "tips": _TIPS, "available_topics": _ALL_TOPICS}
        if topic not in _TIPS:
            return {
                "status": "error",
                "error": f"Unknown topic '{topic}'. Choose one of: {_ALL_TOPICS + ['all']}",
            }
        return {"topic": topic, "tips": _TIPS[topic], "available_topics": _ALL_TOPICS}
