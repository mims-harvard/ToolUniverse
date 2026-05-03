"""
VariantValidator_gene2transcripts

Get all transcripts for a gene using VariantValidator. Returns MANE Select and MANE Plus Clinical...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def VariantValidator_gene2transcripts(
    gene_symbol: str,
    gene: Optional[str] = None,
    gene_name: Optional[str] = None,
    transcript_set: Optional[str] = "mane",
    genome_build: Optional[str] = "GRCh38",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get all transcripts for a gene using VariantValidator. Returns MANE Select and MANE Plus Clinical...

    Parameters
    ----------
    gene_symbol : str
        HGNC gene symbol (e.g., 'TP53', 'BRCA1', 'EGFR'). Aliases: gene, gene_name.
    gene : str
        Alias for gene_symbol.
    gene_name : str
        Alias for gene_symbol.
    transcript_set : str
        Transcript filter: 'mane' for MANE Select/Plus Clinical only, 'refseq' for Re...
    genome_build : str
        Reference genome assembly: 'GRCh37' or 'GRCh38' (default: GRCh38)
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
            "gene_symbol": gene_symbol,
            "gene": gene,
            "gene_name": gene_name,
            "transcript_set": transcript_set,
            "genome_build": genome_build,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "VariantValidator_gene2transcripts",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["VariantValidator_gene2transcripts"]
