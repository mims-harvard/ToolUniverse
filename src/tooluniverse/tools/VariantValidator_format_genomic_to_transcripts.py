"""
VariantValidator_format_genomic_to_transcripts

Project a genomic variant onto EVERY overlapping RefSeq transcript in one call using the VariantV...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def VariantValidator_format_genomic_to_transcripts(
    variant_description: str,
    genome_build: Optional[str] = "GRCh38",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Project a genomic variant onto EVERY overlapping RefSeq transcript in one call using the VariantV...

    Parameters
    ----------
    genome_build : str
        Reference genome assembly: 'GRCh37' (hg19) or 'GRCh38' (hg38).
    variant_description : str
        Genomic-level variant description. Accepts genomic HGVS (e.g. 'NC_000017.11:g...
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
            "genome_build": genome_build,
            "variant_description": variant_description,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "VariantValidator_format_genomic_to_transcripts",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["VariantValidator_format_genomic_to_transcripts"]
