"""
TestCaseGenerator

Generates diverse and representative ToolUniverse tool call dictionaries for a given tool based o...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TestCaseGenerator(
    tool_config: dict[str, Any],
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Generates diverse and representative ToolUniverse tool call dictionaries for a given tool based o...

    Parameters
    ----------
    tool_config : dict[str, Any]
        The full configuration of the tool to generate test cases for. May include '_...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    return get_shared_client().run_one_function(
        {"name": "TestCaseGenerator", "arguments": {"tool_config": tool_config}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TestCaseGenerator"]
