"""
mcp_auto_loader_boltz

Run Boltz2 docking and affinity prediction using MCP protocol
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def mcp_auto_loader_boltz(
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Run Boltz2 docking and affinity prediction using MCP protocol

    Parameters
    ----------
    No parameters
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
        {"name": "mcp_auto_loader_boltz", "arguments": {}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["mcp_auto_loader_boltz"]
