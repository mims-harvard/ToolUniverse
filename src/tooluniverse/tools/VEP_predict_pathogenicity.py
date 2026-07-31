"""
VEP_predict_pathogenicity

Predict missense variant pathogenicity via the Ensembl VEP REST API with AlphaMissense (DeepMind ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def VEP_predict_pathogenicity(
    rsid: Optional[str] = None,
    hgvs_notation: Optional[str] = None,
    chrom: Optional[str] = None,
    pos: Optional[int] = None,
    alt: Optional[str] = None,
    genome_build: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Predict missense variant pathogenicity via the Ensembl VEP REST API with AlphaMissense (DeepMind ...

    Parameters
    ----------
    rsid : str
        dbSNP rsID, e.g. 'rs699' (one input mode)
    hgvs_notation : str
        HGVS notation, e.g. 'ENST00000269305.9:c.524G>A' (one input mode)
    chrom : str
        Chromosome for region input, e.g. '17' (with pos+alt)
    pos : int
        1-based position for region input
    alt : str
        Alternate allele for region input, e.g. 'T'
    genome_build : str
        GRCh38 (default) or GRCh37
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "rsid": rsid,
            "hgvs_notation": hgvs_notation,
            "chrom": chrom,
            "pos": pos,
            "alt": alt,
            "genome_build": genome_build,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "VEP_predict_pathogenicity",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["VEP_predict_pathogenicity"]
