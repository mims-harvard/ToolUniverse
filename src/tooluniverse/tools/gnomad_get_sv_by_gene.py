"""
gnomad_get_sv_by_gene

Get structural variants (SVs) from gnomAD v4 for a gene. Returns deletions, duplications, inversi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def gnomad_get_sv_by_gene(
    gene_symbol: str,
    reference_genome: Optional[str] = "GRCh38",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get structural variants (SVs) from gnomAD v4 for a gene. Returns deletions, duplications, inversi...

    Parameters
    ----------
    gene_symbol : str
        Gene symbol (e.g., 'BRCA1', 'TP53', 'MECP2')
    reference_genome : str
        Reference genome assembly.
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

    return get_shared_client().run_one_function(
        {
            "name": "gnomad_get_sv_by_gene",
            "arguments": {
                "gene_symbol": gene_symbol,
                "reference_genome": reference_genome,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["gnomad_get_sv_by_gene"]
