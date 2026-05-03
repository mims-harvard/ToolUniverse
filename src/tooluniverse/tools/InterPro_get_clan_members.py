"""
InterPro_get_clan_members

Get all member families in a Pfam clan (superfamily) using the InterPro API. Pfam clans group rel...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def InterPro_get_clan_members(
    clan_accession: str,
    max_results: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get all member families in a Pfam clan (superfamily) using the InterPro API. Pfam clans group rel...

    Parameters
    ----------
    clan_accession : str
        Pfam clan accession. Examples: 'CL0016' (PKinase superfamily, 30+ families), ...
    max_results : int
        Maximum number of member families to return (default 50, max 200).
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
            "clan_accession": clan_accession,
            "max_results": max_results,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "InterPro_get_clan_members",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["InterPro_get_clan_members"]
