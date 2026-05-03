"""
Addgene_search_depositors

Search for Addgene depositors (PIs / principal investigators) by name or institution. Returns uni...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Addgene_search_depositors(
    operation: str,
    name: Optional[str | Any] = None,
    institution: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for Addgene depositors (PIs / principal investigators) by name or institution. Returns uni...

    Parameters
    ----------
    operation : str
        Operation type
    name : str | Any
        PI or depositor name to search (e.g., 'Feng Zhang', 'Jennifer Doudna')
    institution : str | Any
        Institution name to search (e.g., 'MIT', 'Broad Institute')
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

    return get_shared_client().run_one_function(
        {
            "name": "Addgene_search_depositors",
            "arguments": {
                "operation": operation,
                "name": name,
                "institution": institution,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Addgene_search_depositors"]
