"""
PRIDE_search_proteomics

Search the PRIDE Archive for proteomics experiments and mass spectrometry datasets. Returns proje...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PRIDE_search_proteomics(
    query: str,
    page_size: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search the PRIDE Archive for proteomics experiments and mass spectrometry datasets. Returns proje...

    Parameters
    ----------
    query : str
        Search keywords for proteomics experiments. Examples: 'cancer', 'phosphorylat...
    page_size : int
        Number of projects to return per page (default: 20, max: 100)
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"query": query, "page_size": page_size}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PRIDE_search_proteomics",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PRIDE_search_proteomics"]
