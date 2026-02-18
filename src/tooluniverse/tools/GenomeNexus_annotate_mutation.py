"""
GenomeNexus_annotate_mutation

Annotate a cancer mutation using Genome Nexus (MSK) by specifying chromosome, start, end, referen...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GenomeNexus_annotate_mutation(
    chromosome: str,
    start: int,
    end: int,
    reference_allele: str,
    variant_allele: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Annotate a cancer mutation using Genome Nexus (MSK) by specifying chromosome, start, end, referen...

    Parameters
    ----------
    chromosome : str
        Chromosome (without 'chr' prefix). Examples: '7', '17', '12', 'X'.
    start : int
        Start position (GRCh37/hg19, 1-based).
    end : int
        End position (GRCh37/hg19, 1-based). Same as start for SNVs.
    reference_allele : str
        Reference allele. Example: 'A'.
    variant_allele : str
        Variant (alternate) allele. Example: 'T'.
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
            "name": "GenomeNexus_annotate_mutation",
            "arguments": {
                "chromosome": chromosome,
                "start": start,
                "end": end,
                "reference_allele": reference_allele,
                "variant_allele": variant_allele,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GenomeNexus_annotate_mutation"]
