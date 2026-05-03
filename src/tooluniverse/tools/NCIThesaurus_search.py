"""
NCIThesaurus_search

Search the NCI Thesaurus (NCIt) for biomedical concepts by term. NCIt is the National Cancer Inst...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCIThesaurus_search(
    term: str,
    page_size: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the NCI Thesaurus (NCIt) for biomedical concepts by term. NCIt is the National Cancer Inst...

    Parameters
    ----------
    term : str
        Search term for NCI concepts. Examples: 'melanoma', 'breast cancer', 'imatini...
    page_size : int | Any
        Number of results to return (default 10, max 100).
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
        k: v for k, v in {"term": term, "page_size": page_size}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NCIThesaurus_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCIThesaurus_search"]
