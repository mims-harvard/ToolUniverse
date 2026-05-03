"""
EVE_get_variant_score

Get EVE (Evolutionary Variant Effect) pathogenicity score for a variant. EVE uses unsupervised de...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EVE_get_variant_score(
    variant: Optional[str] = None,
    chrom: Optional[str] = None,
    pos: Optional[int] = None,
    ref: Optional[str] = None,
    alt: Optional[str] = None,
    species: Optional[str] = "human",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get EVE (Evolutionary Variant Effect) pathogenicity score for a variant. EVE uses unsupervised de...

    Parameters
    ----------
    variant : str
        Variant in HGVS format (e.g., 'ENST00000269305.4:c.100G>A', 'NM_000546.5:c.21...
    chrom : str
        Chromosome (1-22, X, Y). Use with pos, ref, alt instead of variant.
    pos : int
        Genomic position (GRCh38)
    ref : str
        Reference allele
    alt : str
        Alternate allele
    species : str
        Species (default: human)
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "variant": variant,
            "chrom": chrom,
            "pos": pos,
            "ref": ref,
            "alt": alt,
            "species": species,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EVE_get_variant_score",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EVE_get_variant_score"]
