"""
UKBTOPMed_phewas_by_variant

Phenome-wide association study (PheWAS) lookup for a single variant in the UKB-TOPMed PheWeb (UK ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UKBTOPMed_phewas_by_variant(
    rsid: Optional[str] = None,
    variant: Optional[str] = None,
    limit: Optional[int] = 20,
    max_pval: Optional[float] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Phenome-wide association study (PheWAS) lookup for a single variant in the UKB-TOPMed PheWeb (UK ...

    Parameters
    ----------
    rsid : str
        dbSNP rsID, e.g. 'rs7903146'. Auto-resolved to GRCh38 coordinates via Ensembl...
    variant : str
        Variant in chr:pos:ref:alt or chr-pos-ref-alt format, in GRCh38, e.g. '10:112...
    limit : int
        Maximum number of phenotype associations to return (sorted by ascending p-val...
    max_pval : float
        Optional: only return associations with p-value <= this threshold (e.g. 5e-8 ...
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
            "rsid": rsid,
            "variant": variant,
            "limit": limit,
            "max_pval": max_pval,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "UKBTOPMed_phewas_by_variant",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UKBTOPMed_phewas_by_variant"]
