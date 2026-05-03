"""
EU Health Information Portal tools: topic search and deep dive.

This module provides the *wrapper* layer used by the ToolUniverse MCP server.
The actual search logic resides in `tooluniverse.euhealth.tools_runtime`.

What this file does
-------------------
- Maps MCP tool calls → Python functions in tools_runtime.
- For topic search:
      EuHealthTopicSearchTool  →  euhealthinfo_search_<topic>()
- For deep dive:
      EuHealthDeepDiveTool    →  euhealthinfo_deepdive(...)

IMPORTANT
---------
The runtime layer supports *all* search parameters:

  - method: "keyword" | "embedding" | "hybrid"
  - alpha: float
  - top_k: int
  - limit: int
  - country: Optional[str]
  - language: Optional[str]
  - term_override: Optional[str]

This wrapper must forward all these inputs to preserve embedding/hybrid behavior
and ensure correct fallback warnings.
"""

from typing import Dict, Any, List, Optional
from tooluniverse.base_tool import BaseTool
from tooluniverse.tool_registry import register_tool

# The full runtime surface (topic search fns + deep dive)
from tooluniverse.euhealth import tools_runtime as rt


# ---------------------------------------------------------------------
# Topic Search Tool
# ---------------------------------------------------------------------
@register_tool("EuHealthTopicSearchTool")
class EuHealthTopicSearchTool(BaseTool):
    """
    Generic wrapper for all EU Health 'topic search' tools.

    The associated JSON config supplies:
        fields.topic = "euhealthinfo_search_cancer"   (for example)

    Supported arguments:
      - limit: int
      - method: "keyword" | "embedding" | "hybrid"
      - alpha: float
      - top_k: int
      - country: Optional[str]
      - language: Optional[str]
      - term_override: Optional[str]

    Returns:
      Either:
        {"warning": "...", "results": [...]}   (fallback)
      or
        [... shaped rows ...]
    """

    def run(self, arguments: Dict[str, Any]) -> Any:
        topic = (self.tool_config.get("fields") or {}).get("topic")
        if not topic:
            return {
                "error": "EuHealthTopicSearchTool misconfigured: missing fields.topic"
            }

        fn = getattr(rt, topic, None)
        if fn is None or not callable(fn):
            return {"error": f"Topic function '{topic}' not found in tools_runtime"}

        # ---- pull ALL supported parameters ----
        limit = int(arguments.get("limit", 25))
        method = arguments.get("method", "hybrid")
        alpha = float(arguments.get("alpha", 0.5))
        top_k = int(arguments.get("top_k", 25))
        country = arguments.get("country", "")
        language = arguments.get("language", "")
        term_override = arguments.get("term_override", "")

        try:
            # ---- forward ALL parameters ----
            return fn(
                limit=limit,
                method=method,
                alpha=alpha,
                top_k=top_k,
                country=country,
                language=language,
                term_override=term_override,
            )
        except Exception as e:
            return {"error": f"euhealth topic search failed: {e}", "topic": topic}


# ---------------------------------------------------------------------
# Deep Dive Tool
# ---------------------------------------------------------------------
@register_tool("EuHealthDeepDiveTool")
class EuHealthDeepDiveTool(BaseTool):
    """
    Wrapper for the EU Health deep dive function.

    You can dive:
      - explicit UUIds: uuids=[...]
      - or a topic: topic="euhealthinfo_search_cancer"

    Supported arguments:
      - uuids: Optional[List[str]]
      - topic: Optional[str]
      - limit: int
      - links_per: int
      - method: "keyword" | "embedding" | "hybrid"
      - alpha: float
      - top_k: int
      - country: Optional[str]
      - language: Optional[str]
      - term_override: Optional[str]
    """

    def run(self, arguments: Dict[str, Any]) -> Any:
        uuids = arguments.get("uuids")
        topic = arguments.get("topic")
        limit = int(arguments.get("limit", 10))
        links_per = int(arguments.get("links_per", 3))

        method = arguments.get("method", "hybrid")
        alpha = float(arguments.get("alpha", 0.5))
        top_k = int(arguments.get("top_k", 25))
        country = arguments.get("country", "")
        language = arguments.get("language", "")
        term_override = arguments.get("term_override", "")

        if not uuids and not topic:
            return {"error": "Provide either 'uuids' or 'topic' to run deep dive"}

        try:
            if uuids:
                return rt.euhealthinfo_deepdive(
                    uuids=uuids,
                    limit=limit,
                    links_per=links_per,
                    method=method,
                    alpha=alpha,
                    top_k=top_k,
                    country=country,
                    language=language,
                    term_override=term_override,
                )
            else:
                if not hasattr(rt, topic):
                    return {"error": f"Unknown topic '{topic}' for deep dive"}

                return rt.euhealthinfo_deepdive(
                    topic=topic,
                    limit=limit,
                    links_per=links_per,
                    method=method,
                    alpha=alpha,
                    top_k=top_k,
                    country=country,
                    language=language,
                    term_override=term_override,
                )

        except Exception as e:
            return {"error": f"euhealth deep dive failed: {e}"}
