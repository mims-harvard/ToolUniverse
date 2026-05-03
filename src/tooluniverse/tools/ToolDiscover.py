"""
ToolDiscover

Generates new ToolUniverse-compliant tools based on short descriptions using XML format for simul...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ToolDiscover(
    tool_description: str,
    max_iterations: Optional[int] = 2,
    save_to_file: Optional[bool] = True,
    output_file: Optional[str] = None,
    save_dir: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Generates new ToolUniverse-compliant tools based on short descriptions using XML format for simul...

    Parameters
    ----------
    tool_description : str
        Short description of the desired tool functionality
    max_iterations : int
        Maximum number of optimization iterations
    save_to_file : bool
        Whether to save the generated tool files
    output_file : str
        Optional file path to save the generated tool
    save_dir : str
        Directory path to save the generated tool files (defaults to current working ...
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "tool_description": tool_description,
            "max_iterations": max_iterations,
            "save_to_file": save_to_file,
            "output_file": output_file,
            "save_dir": save_dir,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ToolDiscover",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ToolDiscover"]
