"""
HuggingFace_search_models

Search the HuggingFace Hub for machine learning models by keyword, task type, or ML framework. Hu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HuggingFace_search_models(
    search: str,
    limit: Optional[int | Any] = None,
    pipeline_tag: Optional[str | Any] = None,
    library: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the HuggingFace Hub for machine learning models by keyword, task type, or ML framework. Hu...

    Parameters
    ----------
    search : str
        Search query for model name, task, or topic (e.g., 'protein language model', ...
    limit : int | Any
        Maximum number of results to return (default 20, max 1000)
    pipeline_tag : str | Any
        Filter by ML task type. Common values: 'text-classification', 'token-classifi...
    library : str | Any
        Filter by ML framework/library. Common values: 'transformers', 'diffusers', '...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Any
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {
        "search": search,
                "limit": limit,
                "pipeline_tag": pipeline_tag,
                "library": library
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "HuggingFace_search_models",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["HuggingFace_search_models"]
