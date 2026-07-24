"""
Pathoplexus_get_sequences_fasta

Download the actual genome sequences (FASTA) from Pathoplexus/LAPIS for a surveilled pathogen. Re...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Pathoplexus_get_sequences_fasta(
    organism: str,
    country: Optional[str] = None,
    lineage: Optional[str] = None,
    sequence_type: Optional[str] = None,
    aligned: Optional[bool] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Download the actual genome sequences (FASTA) from Pathoplexus/LAPIS for a surveilled pathogen. Re...

    Parameters
    ----------
    organism : str
        Pathoplexus organism slug: 'west-nile', 'ebola-zaire', 'ebola-sudan', 'cchf',...
    country : str
        Filter by country (geoLocCountry), e.g. 'USA'.
    lineage : str
        Filter by lineage.
    sequence_type : str
        'nucleotide' (default) or 'aminoAcid'.
    aligned : bool
        Return aligned sequences instead of unaligned (default false).
    limit : int
        Number of sequences to download (default 1, max 100).
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
            "sequence_type": sequence_type,
            "aligned": aligned,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Pathoplexus_get_sequences_fasta",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Pathoplexus_get_sequences_fasta"]
