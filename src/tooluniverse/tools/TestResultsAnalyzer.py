"""
TestResultsAnalyzer

Analyzes test execution results and extracts key issues for targeted optimization
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TestResultsAnalyzer(
    test_results: str,
    tool_implementation: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Analyzes test execution results and extracts key issues for targeted optimization

    Parameters
    ----------
    test_results : str
        JSON string containing test execution results with pass/fail status, error me...
    tool_implementation : str
        Current tool implementation code for context
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
            "name": "TestResultsAnalyzer",
            "arguments": {
                "test_results": test_results,
                "tool_implementation": tool_implementation,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TestResultsAnalyzer"]
