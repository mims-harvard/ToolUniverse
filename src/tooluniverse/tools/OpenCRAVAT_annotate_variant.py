"""
OpenCRAVAT_annotate_variant

Annotate a single genomic variant using OpenCRAVAT with 182+ annotation sources including ClinVar...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenCRAVAT_annotate_variant(
    chrom: Optional[str] = None,
    chromosome: Optional[str] = None,
    pos: Optional[int] = None,
    position: Optional[int] = None,
    ref_base: Optional[str] = None,
    ref: Optional[str] = None,
    alt_base: Optional[str] = None,
    alt: Optional[str] = None,
    annotators: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Annotate a single genomic variant using OpenCRAVAT with 182+ annotation sources including ClinVar...

    Parameters
    ----------
    chrom : str
        Chromosome (e.g., 'chr17', 'chr7', '17'). 'chr' prefix added automatically if...
    chromosome : str
        Alias for chrom. Chromosome (e.g., 'chr17', 'chr7', '17').
    pos : int
        Genomic position (1-based, GRCh38 coordinates)
    position : int
        Alias for pos. Genomic position (1-based, GRCh38 coordinates).
    ref_base : str
        Reference allele (e.g., 'C', 'A', 'G', 'T')
    ref : str
        Alias for ref_base. Reference allele.
    alt_base : str
        Alternate allele (e.g., 'T', 'A', 'G', 'C')
    alt : str
        Alias for alt_base. Alternate allele.
    annotators : str
        Comma-separated annotator names (e.g., 'clinvar,gnomad3,sift,polyphen2,revel,...
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
            "chrom": chrom,
            "chromosome": chromosome,
            "pos": pos,
            "position": position,
            "ref_base": ref_base,
            "ref": ref,
            "alt_base": alt_base,
            "alt": alt,
            "annotators": annotators,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenCRAVAT_annotate_variant",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenCRAVAT_annotate_variant"]
