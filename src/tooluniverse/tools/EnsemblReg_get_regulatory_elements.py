"""
EnsemblReg_get_regulatory_elements

Get Ensembl regulatory features (enhancers, promoters, CTCF binding sites, open chromatin, TF bin...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EnsemblReg_get_regulatory_elements(
    chrom: str,
    start: int,
    end: int,
    species: Optional[str] = "homo_sapiens",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get Ensembl regulatory features (enhancers, promoters, CTCF binding sites, open chromatin, TF bin...

    Parameters
    ----------
    species : str
        Species name (e.g., 'homo_sapiens', 'mus_musculus').
    chrom : str
        Chromosome number without 'chr' prefix (e.g., '17', '7', 'X').
    start : int
        Start position (1-based).
    end : int
        End position (1-based).
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
            "species": species,
            "chrom": chrom,
            "start": start,
            "end": end,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EnsemblReg_get_regulatory_elements",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EnsemblReg_get_regulatory_elements"]
