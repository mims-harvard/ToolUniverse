"""
AlphaGenome_score_variant

Score a regulatory variant's effect with DeepMind AlphaGenome (Avsec, Nature 2026), the hosted su...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def AlphaGenome_score_variant(
    chromosome: str,
    position: int,
    reference_bases: str,
    alternate_bases: str,
    output_type: Optional[str] = None,
    organism: Optional[str] = None,
    sequence_length: Optional[str] = None,
    top_n: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Score a regulatory variant's effect with DeepMind AlphaGenome (Avsec, Nature 2026), the hosted su...

    Parameters
    ----------
    chromosome : str
        Chromosome, e.g. 'chr22'.
    position : int
        1-based variant position.
    reference_bases : str
        Reference allele, e.g. 'A'.
    alternate_bases : str
        Alternate allele, e.g. 'C'.
    output_type : str
        Modality to score: RNA_SEQ (default), ATAC, DNASE, CAGE, CHIP_HISTONE, CHIP_T...
    organism : str
        'human' (default) or 'mouse'.
    sequence_length : str
        Context window: 16KB, 100KB, 500KB, or 1MB (default).
    top_n : int
        Number of top |effect| tracks to return (default 20).
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
            "chromosome": chromosome,
            "position": position,
            "reference_bases": reference_bases,
            "alternate_bases": alternate_bases,
            "output_type": output_type,
            "organism": organism,
            "sequence_length": sequence_length,
            "top_n": top_n,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "AlphaGenome_score_variant",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["AlphaGenome_score_variant"]
