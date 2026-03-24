"""
Progenetix_search_individuals

Search individuals (patients) in the Progenetix cancer CNV database by NCIt disease ontology code.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Progenetix_search_individuals(
    filters: str,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search individuals (patients) in Progenetix by NCIt disease code.

    Parameters
    ----------
    filters : str
        NCIt ontology code (e.g., 'NCIT:C9145' for AML, 'NCIT:C3058' for Glioblastoma).
    limit : int, optional
        Maximum number of individuals to return (default 10, max 100).
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
        k: v for k, v in {"filters": filters, "limit": limit}.items() if v is not None
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
