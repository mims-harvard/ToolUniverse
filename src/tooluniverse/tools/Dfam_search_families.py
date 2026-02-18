"""
Dfam_search_families

Search Dfam for transposable element (TE) / repeat element families by name prefix, taxonomic cla...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Dfam_search_families(
    name_prefix: Optional[str] = None,
    clade: Optional[str] = None,
    repeat_type: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search Dfam for transposable element (TE) / repeat element families by name prefix, taxonomic cla...

    Parameters
    ----------
    name_prefix : str
        TE family name prefix to search (e.g., 'AluS', 'L1M', 'SVA', 'MER'). Case-sen...
    clade : str
        Taxonomic clade filter as NCBI taxon ID (e.g., '9606' for human, '40674' for ...
    repeat_type : str
        Repeat type filter. Options: 'SINE', 'LINE', 'LTR', 'DNA', 'Satellite', 'RC',...
    limit : int
        Maximum number of results (default 20, max 50).
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
            "name": "Dfam_search_families",
            "arguments": {
                "name_prefix": name_prefix,
                "clade": clade,
                "repeat_type": repeat_type,
                "limit": limit,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Dfam_search_families"]
