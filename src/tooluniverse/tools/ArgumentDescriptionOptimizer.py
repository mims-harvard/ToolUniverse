"""
ArgumentDescriptionOptimizer

Optimizes the descriptions of tool arguments/parameters based on test case results and actual usa...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ArgumentDescriptionOptimizer(
    parameter_schema: str,
    test_results: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Optimizes the descriptions of tool arguments/parameters based on test case results and actual usa...

    Parameters
    ----------
    parameter_schema : str
        JSON string of the original parameter schema with properties and descriptions.
    test_results : str
        A JSON string containing test case input/output pairs showing parameter usage.
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
            "name": "ArgumentDescriptionOptimizer",
            "arguments": {
                "parameter_schema": parameter_schema,
                "test_results": test_results,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ArgumentDescriptionOptimizer"]
