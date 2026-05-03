"""
GlyGen_search_glycans

Search GlyGen for glycans by mass range, monosaccharide count, organism, or glycan type. Returns ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GlyGen_search_glycans(
    mass_min: Optional[float] = None,
    mass_max: Optional[float] = None,
    monosaccharide_min: Optional[int] = None,
    monosaccharide_max: Optional[int] = None,
    glycan_type: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search GlyGen for glycans by mass range, monosaccharide count, organism, or glycan type. Returns ...

    Parameters
    ----------
    mass_min : float
        Minimum molecular mass in Daltons. Example: 1000.
    mass_max : float
        Maximum molecular mass in Daltons. Example: 3000.
    monosaccharide_min : int
        Minimum number of monosaccharide residues.
    monosaccharide_max : int
        Maximum number of monosaccharide residues.
    glycan_type : str
        Glycan type filter. Examples: 'N-linked', 'O-linked'.
    limit : int
        Maximum results to return (default 20, max 50).
    offset : int
        Pagination offset (1-indexed, default 1).
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
            "mass_min": mass_min,
            "mass_max": mass_max,
            "monosaccharide_min": monosaccharide_min,
            "monosaccharide_max": monosaccharide_max,
            "glycan_type": glycan_type,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GlyGen_search_glycans",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GlyGen_search_glycans"]
