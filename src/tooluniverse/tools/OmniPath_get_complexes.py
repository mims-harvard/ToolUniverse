"""
OmniPath_get_complexes

Get protein complex compositions from OmniPath's comprehensive complex database. Integrates 22,00...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OmniPath_get_complexes(
    proteins: str,
    databases: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get protein complex compositions from OmniPath's comprehensive complex database. Integrates 22,00...

    Parameters
    ----------
    proteins : str
        UniProt accession(s), comma-separated. Note: gene symbols are NOT supported f...
    databases : str | Any
        Filter by source database(s), comma-separated. Options: CORUM, CellPhoneDB, C...
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
            "name": "OmniPath_get_complexes",
            "arguments": {"proteins": proteins, "databases": databases},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OmniPath_get_complexes"]
