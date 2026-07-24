"""
Pathoplexus_get_sequence_details

List the individual sequence records (not aggregated counts) behind a Pathoplexus organism, from ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Pathoplexus_get_sequence_details(
    organism: str,
    country: Optional[str] = None,
    lineage: Optional[str] = None,
    fields: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List the individual sequence records (not aggregated counts) behind a Pathoplexus organism, from ...

    Parameters
    ----------
    organism : str
        Pathoplexus organism slug: 'west-nile', 'ebola-zaire', 'ebola-sudan', 'cchf',...
    country : str
        Filter by country (geoLocCountry), e.g. 'USA'.
    lineage : str
        Filter by lineage.
    fields : str
        Comma-separated metadata fields to return, e.g. 'accession,geoLocCountry,samp...
    limit : int
        Max sequence rows (default 50, max 1000).
    offset : int
        Row offset for pagination (default 0).
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
            "organism": organism,
            "country": country,
            "lineage": lineage,
            "fields": fields,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Pathoplexus_get_sequence_details",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Pathoplexus_get_sequence_details"]
