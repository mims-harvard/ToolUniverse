"""
DescriptionQualityEvaluator

Evaluates the quality of tool descriptions and parameter descriptions, providing a score and spec...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DescriptionQualityEvaluator(
    tool_description: str,
    parameter_descriptions: str,
    test_results: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Evaluates the quality of tool descriptions and parameter descriptions, providing a score and spec...

    Parameters
    ----------
    tool_description : str
        The tool description to evaluate.
    parameter_descriptions : str
        JSON string of parameter names and their descriptions.
    test_results : str
        JSON string containing test case results.
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
            "name": "DescriptionQualityEvaluator",
            "arguments": {
                "tool_description": tool_description,
                "parameter_descriptions": parameter_descriptions,
                "test_results": test_results,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DescriptionQualityEvaluator"]
