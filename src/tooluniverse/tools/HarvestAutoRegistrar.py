"""
HarvestAutoRegistrar

Compose workflow that harvests candidate APIs, validates them, and registers a
new verified-source tool. Optionally executes the registered tool immediately.
"""

from typing import Any, Dict, List, Optional, Callable
from ._shared_client import get_shared_client


def HarvestAutoRegistrar(
    query: Optional[str] = None,
    limit: int = 5,
    *,
    harvest: Optional[Dict[str, Any]] = None,
    candidates: Optional[List[Dict[str, Any]]] = None,
    tester: Optional[Dict[str, Any]] = None,
    register: Optional[Dict[str, Any]] = None,
    tool_name: Optional[str] = None,
    force_register: bool = False,
    force: bool = False,
    skip_tests: bool = False,
    auto_run: bool = False,
    tool_arguments: Optional[Dict[str, Any]] = None,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Discover, validate, and register a verified-source tool in a single call.

    Parameters
    ----------
    query : str, optional
        Harvest query when candidates are not supplied directly.
    limit : int, default 5
        Maximum number of harvest candidates to inspect.
    harvest : dict, optional
        Additional arguments forwarded to GenericHarvestTool.
    candidates : list, optional
        Precomputed candidate objects. Skips calling GenericHarvestTool when provided.
    tester : dict, optional
        Overrides forwarded to HarvestCandidateTesterTool.
    register : dict, optional
        Overrides forwarded to VerifiedSourceRegisterTool.
    tool_name : str, optional
        Desired name for the registered tool. Auto-generated if omitted.
    force_register : bool, default False
        Register even when validation fails (mirrors VerifiedSourceRegisterTool.force).
    force : bool, default False
        Alias for force_register for convenience.
    skip_tests : bool, default False
        Bypass HarvestCandidateTesterTool and proceed straight to registration.
    auto_run : bool, default False
        Execute the registered tool immediately after a successful registration.
    tool_arguments : dict, optional
        Arguments forwarded to the registered tool when auto_run is True.
    stream_callback : Callable, optional
        Streaming callback handled by ToolUniverse shared client.
    use_cache : bool, default False
        Enable client-side caching.
    validate : bool, default True
        Validate payload before sending to ToolUniverse.
    """
    payload = {
        "name": "HarvestAutoRegistrar",
        "arguments": {
            "query": query,
            "limit": limit,
            "harvest": harvest,
            "candidates": candidates,
            "tester": tester,
            "register": register,
            "tool_name": tool_name,
            "force_register": force_register or force,
            "skip_tests": skip_tests,
            "auto_run": auto_run,
            "tool_arguments": tool_arguments or {},
        },
    }

    return get_shared_client().run_one_function(
        payload,
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HarvestAutoRegistrar"]
