"""
Progenetix_search_biosamples

Search cancer tumor biosamples in the Progenetix database by NCIt disease ontology code. Progenet...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Progenetix_search_biosamples(
    filters: str,
    limit: Optional[int] = 10,
    skip: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search cancer tumor biosamples in the Progenetix database by NCIt disease ontology code. Progenet...

    Parameters
    ----------
    filters : str
        NCIt ontology code to filter biosamples by cancer type. Examples: 'NCIT:C3058...
    limit : int
        Maximum number of biosamples to return (default: 10).
    skip : int
        Number of results to skip for pagination (default: 0).
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"filters": filters, "limit": limit, "skip": skip}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Progenetix_search_biosamples",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Progenetix_search_biosamples"]
