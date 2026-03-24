"""
Progenetix_search_biosamples

Search cancer tumor biosamples in the Progenetix database by NCIt disease ontology code.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Progenetix_search_biosamples(
    filters: str,
    limit: Optional[int] = None,
    skip: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search cancer tumor biosamples in Progenetix by NCIt disease code.

    Parameters
    ----------
    filters : str
        NCIt ontology code (e.g., 'NCIT:C3058' for Glioblastoma, 'NCIT:C4017' for Breast Carcinoma).
    limit : int, optional
        Maximum number of biosamples to return (default 10, max 100).
    skip : int, optional
        Number of results to skip for pagination (default 0).
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
