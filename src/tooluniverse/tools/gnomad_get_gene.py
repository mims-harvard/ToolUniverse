"""
gnomad_get_gene

Get basic gene metadata from gnomAD by `gene_symbol` or `gene_id` (Ensembl gene ID). Use `gnomad_...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def gnomad_get_gene(
    gene_symbol: Optional[str] = None,
    gene_id: Optional[str] = None,
    reference_genome: Optional[str] = "GRCh38",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get basic gene metadata from gnomAD by `gene_symbol` or `gene_id` (Ensembl gene ID). Use `gnomad_...

    Parameters
    ----------
    gene_symbol : str
        Gene symbol (e.g., 'BRCA1').
    gene_id : str
        Ensembl gene ID (e.g., 'ENSG00000012048').
    reference_genome : str
        Reference genome.
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
            "gene_symbol": gene_symbol,
            "gene_id": gene_id,
            "reference_genome": reference_genome,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "gnomad_get_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["gnomad_get_gene"]
