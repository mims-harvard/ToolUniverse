"""
Pathoplexus_count_sequences

Count and aggregate open pathogen genome sequences in Pathoplexus (LAPIS) for genomic-epidemiolog...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Pathoplexus_count_sequences(
    organism: str,
    country: Optional[str] = None,
    lineage: Optional[str] = None,
    group_by: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Count and aggregate open pathogen genome sequences in Pathoplexus (LAPIS) for genomic-epidemiolog...

    Parameters
    ----------
    organism : str
        Pathoplexus organism slug: 'west-nile', 'ebola-zaire', 'ebola-sudan', 'cchf',...
    country : str
        Filter by country (geoLocCountry), e.g. 'USA'.
    lineage : str
        Filter by lineage.
    group_by : str
        Metadata field to group counts by, e.g. 'geoLocCountry', 'lineage', 'sampleCo...
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
            "group_by": group_by,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Pathoplexus_count_sequences",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Pathoplexus_count_sequences"]
