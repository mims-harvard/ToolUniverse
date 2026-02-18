"""
CodeQualityAnalyzer

Analyzes code quality from multiple dimensions including algorithmic correctness, functional impl...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CodeQualityAnalyzer(
    tool_name: str,
    tool_description: str,
    tool_parameters: str,
    implementation_code: str,
    test_cases: str,
    test_execution_results: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Analyzes code quality from multiple dimensions including algorithmic correctness, functional impl...

    Parameters
    ----------
    tool_name : str
        Name of the tool being analyzed
    tool_description : str
        Description of what the tool is supposed to do
    tool_parameters : str
        JSON string of tool parameters and their types
    implementation_code : str
        The actual implementation code to analyze
    test_cases : str
        JSON string of test cases for the tool
    test_execution_results : str
        JSON string of test execution results including pass/fail status and actual o...
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
            "name": "CodeQualityAnalyzer",
            "arguments": {
                "tool_name": tool_name,
                "tool_description": tool_description,
                "tool_parameters": tool_parameters,
                "implementation_code": implementation_code,
                "test_cases": test_cases,
                "test_execution_results": test_execution_results,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CodeQualityAnalyzer"]
