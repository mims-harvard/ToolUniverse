"""
DescriptionAnalyzer

Analyzes a tool's original description and the results of multiple test cases, then suggests an i...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DescriptionAnalyzer(
    original_description: str,
    test_results: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Analyzes a tool's original description and the results of multiple test cases, then suggests an i...

    Parameters
    ----------
    original_description : str
        The original description of the tool.
    test_results : str
        A JSON string containing a list of test case input/output pairs.
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
        {
            "name": "DescriptionAnalyzer",
            "arguments": {
                "original_description": original_description,
                "test_results": test_results,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DescriptionAnalyzer"]
