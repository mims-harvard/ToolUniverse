"""
BVBRC_get_genome

Get the complete genome record exposed by BV-BRC, including all assembly, quality, CheckM, access...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BVBRC_get_genome(
    genome_id: str,
    include_related: Optional[bool] = False,
    related_limit: Optional[int] = 25,
    related_offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the complete genome record exposed by BV-BRC, including all assembly, quality, CheckM, access...

    Parameters
    ----------
    genome_id : str
        BV-BRC genome identifier (taxon_id.version format). Examples: '83332.12' (M. ...
    include_related : bool
        Also retrieve paginated AMR phenotype and specialty-gene records for this exa...
    related_limit : int
        Maximum AMR and specialty-gene records returned per related collection.
    related_offset : int
        Zero-based offset for both related collections. Their independent next offset...
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
            "genome_id": genome_id,
            "include_related": include_related,
            "related_limit": related_limit,
            "related_offset": related_offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BVBRC_get_genome",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BVBRC_get_genome"]
