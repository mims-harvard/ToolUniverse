"""
VSDResolveCapability

Check a requested capability against registered ToolUniverse tools and composed workflows before ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def VSDResolveCapability(
    description: str,
    provider: Optional[str] = None,
    method: Optional[str] = "GET",
    endpoint: Optional[str] = None,
    operation_id: Optional[str] = None,
    required_inputs: Optional[list[str]] = None,
    output_fields: Optional[list[str]] = None,
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Check a requested capability against registered ToolUniverse tools and composed workflows before ...

    Parameters
    ----------
    description : str
        Non-sensitive description of the required capability.
    provider : str
        Optional provider name or HTTPS provider URL.
    method : str

    endpoint : str
        Optional exact HTTPS operation endpoint without query parameters.
    operation_id : str
        Optional stable provider operation identifier.
    required_inputs : list[str]

    output_fields : list[str]

    limit : int

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
    if required_inputs is None:
        required_inputs = []
    if output_fields is None:
        output_fields = []
    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "description": description,
            "provider": provider,
            "method": method,
            "endpoint": endpoint,
            "operation_id": operation_id,
            "required_inputs": required_inputs,
            "output_fields": output_fields,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "VSDResolveCapability",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["VSDResolveCapability"]
