"""
NeuroMorpho_get_literature

Get a single source-publication (literature) record by its NeuroMorpho article_id. Returns the fu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NeuroMorpho_get_literature(
    article_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get a single source-publication (literature) record by its NeuroMorpho article_id. Returns the fu...

    Parameters
    ----------
    article_id : str
        NeuroMorpho internal article ID from NeuroMorpho_search_literature. Example: ...
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
    _args = {k: v for k, v in {"article_id": article_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "NeuroMorpho_get_literature",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NeuroMorpho_get_literature"]
