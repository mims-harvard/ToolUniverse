"""
NCBIVariation_vcf_to_spdi

Convert a raw VCF four-field variant (chromosome RefSeq accession, position, reference allele, al...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCBIVariation_vcf_to_spdi(
    chrom: str,
    pos: str,
    ref: str,
    alt: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Convert a raw VCF four-field variant (chromosome RefSeq accession, position, reference allele, al...

    Parameters
    ----------
    chrom : str
        Chromosome RefSeq accession (e.g., 'NC_000007.14' for chr7 GRCh38, 'NC_000019...
    pos : str
        1-based VCF position (e.g., '140753336' for BRAF V600E, '44908684' for APOE r...
    ref : str
        Reference allele (e.g., 'A', 'T', 'G', 'C')
    alt : str
        Alternate allele (e.g., 'T', 'C'). Single allele; comma-separated alts also a...
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
        for k, v in {"chrom": chrom, "pos": pos, "ref": ref, "alt": alt}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NCBIVariation_vcf_to_spdi",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCBIVariation_vcf_to_spdi"]
