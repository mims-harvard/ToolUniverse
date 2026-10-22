"""
Progenetix_search_individuals

Search individuals (patients) in the Progenetix cancer CNV database by NCIt disease code. Returns...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Progenetix_search_individuals(
    filters: str,
    limit: Optional[int] = 10,
    skip: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search individuals (patients) in the Progenetix cancer CNV database by NCIt disease code. Returns...

    Parameters
    ----------
    filters : str
        NCIt ontology code to filter individuals by cancer type. Examples: 'NCIT:C914...
    limit : int
        Maximum number of individuals to return (default: 10).
    skip : int
        Number of matching individuals to skip. Use next_skip from the preceding resp...
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
            "name": "Progenetix_search_individuals",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Progenetix_search_individuals"]
