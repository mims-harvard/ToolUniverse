"""
EnsemblSeq_get_region_sequence

Get the DNA nucleotide sequence for a specific genomic region from Ensembl. Retrieves the referen...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EnsemblSeq_get_region_sequence(
    region: str,
    species: Optional[str] = "homo_sapiens",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the DNA nucleotide sequence for a specific genomic region from Ensembl. Retrieves the referen...

    Parameters
    ----------
    region : str
        Genomic region in format 'chr:start-end' or 'chr:start..end:strand'. Examples...
    species : str
        Ensembl species name. Default: 'homo_sapiens'. Examples: 'mus_musculus', 'dan...
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
            "name": "EnsemblSeq_get_region_sequence",
            "arguments": {"region": region, "species": species},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EnsemblSeq_get_region_sequence"]
