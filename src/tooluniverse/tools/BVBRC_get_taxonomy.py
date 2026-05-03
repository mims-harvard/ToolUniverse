"""
BVBRC_get_taxonomy

Get detailed taxonomy information for a pathogen from BV-BRC by NCBI Taxonomy ID. Returns taxon n...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BVBRC_get_taxonomy(
    taxon_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed taxonomy information for a pathogen from BV-BRC by NCBI Taxonomy ID. Returns taxon n...

    Parameters
    ----------
    taxon_id : str
        NCBI Taxonomy ID. Examples: '2697049' (SARS-CoV-2), '1773' (M. tuberculosis),...
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
    _args = {k: v for k, v in {"taxon_id": taxon_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "BVBRC_get_taxonomy",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BVBRC_get_taxonomy"]
