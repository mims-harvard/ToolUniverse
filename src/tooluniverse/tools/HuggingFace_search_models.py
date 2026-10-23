"""
HuggingFace_search_models

Search the HuggingFace Hub for machine learning models. Results use the Hub's opaque cursor pagin...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HuggingFace_search_models(
    search: str,
    limit: Optional[int] = 20,
    cursor: Optional[str] = None,
    pipeline_tag: Optional[str] = None,
    library: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the HuggingFace Hub for machine learning models. Results use the Hub's opaque cursor pagin...

    Parameters
    ----------
    search : str
        Search query for model name, task, or topic (e.g., 'protein language model', ...
    limit : int
        Results per cursor page (default 20, max 1000)
    cursor : str
        Opaque continuation cursor from metadata.next_cursor. Omit on the first page.
    pipeline_tag : str
        Filter by ML task type. Common values: 'text-classification', 'token-classifi...
    library : str
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
    _args = {
        k: v
        for k, v in {
            "search": search,
            "limit": limit,
            "cursor": cursor,
            "pipeline_tag": pipeline_tag,
            "library": library,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HuggingFace_search_models",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HuggingFace_search_models"]
