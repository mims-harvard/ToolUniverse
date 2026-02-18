"""
ToolQualityEvaluator

Evaluates the quality of tool configurations and implementations. Provides detailed scoring and f...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ToolQualityEvaluator(
    tool_config: str,
    test_cases: str,
    evaluation_aspects: list[Any],
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Evaluates the quality of tool configurations and implementations. Provides detailed scoring and f...

    Parameters
    ----------
    tool_config : str
        JSON string of the tool configuration
    test_cases : str
        JSON string of test cases
    evaluation_aspects : list[Any]
        Aspects to evaluate (functionality, usability, completeness, best_practices)
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
            "name": "ToolQualityEvaluator",
            "arguments": {
                "tool_config": tool_config,
                "test_cases": test_cases,
                "evaluation_aspects": evaluation_aspects,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ToolQualityEvaluator"]
