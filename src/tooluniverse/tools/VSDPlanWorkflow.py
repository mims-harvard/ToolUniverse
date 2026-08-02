"""
VSDPlanWorkflow

Preflight an agent-proposed multi-step workflow against registered ToolUniverse tools and composed workflows.
"""

from typing import Any, Callable, Optional

from ._shared_client import get_shared_client


def VSDPlanWorkflow(
    goal: str,
    capabilities: list[dict[str, Any]],
    limit: Optional[int] = 5,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """Preflight a workflow without executing, persisting, or reporting it."""
    arguments = {
        key: value
        for key, value in {
            "goal": goal,
            "capabilities": capabilities,
            "limit": limit,
        }.items()
        if value is not None
    }
    return get_shared_client().run_one_function(
        {"name": "VSDPlanWorkflow", "arguments": arguments},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["VSDPlanWorkflow"]
