"""
MAGICapp_list_guidelines

Find clinical practice guidelines on MAGICapp (Making GRADE the Irresistible Choice), the platfor...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MAGICapp_list_guidelines(
    query: Optional[str] = None,
    language: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Find clinical practice guidelines on MAGICapp (Making GRADE the Irresistible Choice), the platfor...

    Parameters
    ----------
    query : str
        Words to find in a guideline's name, organization or description, e.g. 'strok...
    language : str
        Language code to keep, e.g. 'en' (also matches 'en-gb'), 'nl', 'dk'. Omit for...
    limit : int
        Guidelines to return (default 20, at most 100).
    offset : int
        Matching guidelines to skip, for paging (metadata.next_offset).
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
            "query": query,
            "language": language,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MAGICapp_list_guidelines",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MAGICapp_list_guidelines"]
