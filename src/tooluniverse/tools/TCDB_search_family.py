"""
TCDB_search_family

Search TCDB transporter families by TC family ID prefix or family name text. Returns matching fam...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TCDB_search_family(
    family_id: Optional[str] = None,
    family_name: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search TCDB transporter families by TC family ID prefix or family name text. Returns matching fam...

    Parameters
    ----------
    family_id : str
        TC family ID or prefix to search (e.g., '2.A.1' for Major Facilitator Superfa...
    family_name : str
        Text to search in family descriptions (e.g., 'Major Facilitator', 'ABC', 'glu...
    limit : int
        Maximum number of families to return per page (default 20, max 100). This cap...
    offset : int
        Number of matching families to skip before returning a page (default 0). Comb...
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
            "family_id": family_id,
            "family_name": family_name,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "TCDB_search_family",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TCDB_search_family"]
