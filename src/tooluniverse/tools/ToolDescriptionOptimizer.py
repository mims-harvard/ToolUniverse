"""
ToolDescriptionOptimizer

Optimizes a tool's description and parameter descriptions by generating test cases, executing the...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ToolDescriptionOptimizer(
    tool_config: dict[str, Any],
    save_to_file: bool,
    output_file: str,
    max_iterations: int,
    satisfaction_threshold: float,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Optimizes a tool's description and parameter descriptions by generating test cases, executing the...

    Parameters
    ----------
    tool_config : dict[str, Any]
        The full configuration of the tool to optimize.
    save_to_file : bool
        If true, save the optimized description to a file (do not overwrite the origi...
    output_file : str
        Optional file path to save the optimized description. If not provided, use '<...
    max_iterations : int
        Maximum number of optimization rounds to perform.
    satisfaction_threshold : float
        Quality score threshold (1-10) to consider optimization satisfactory.
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
            "tool_config": tool_config,
            "save_to_file": save_to_file,
            "output_file": output_file,
            "max_iterations": max_iterations,
            "satisfaction_threshold": satisfaction_threshold,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ToolDescriptionOptimizer",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ToolDescriptionOptimizer"]
