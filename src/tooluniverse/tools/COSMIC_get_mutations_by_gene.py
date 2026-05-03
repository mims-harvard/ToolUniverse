"""
COSMIC_get_mutations_by_gene

Get all somatic mutations for a specific gene from COSMIC database. Returns comprehensive mutatio...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def COSMIC_get_mutations_by_gene(
    operation: Optional[str] = None,
    gene: Optional[str] = None,
    gene_name: Optional[str] = None,
    max_results: Optional[int] = 100,
    genome_build: Optional[int] = 37,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get all somatic mutations for a specific gene from COSMIC database. Returns comprehensive mutatio...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_by_gene)
    gene : str
        Gene symbol (e.g., BRAF, TP53, EGFR, KRAS, PIK3CA). Alias: gene_name also acc...
    gene_name : str
        Alias for gene parameter. Gene symbol (e.g., FLT3, BRAF, TP53).
    max_results : int
        Maximum number of mutations to return (default: 100, max: 500)
    genome_build : int
        Genome build version: 37 (GRCh37/hg19) or 38 (GRCh38/hg38). Default: 37
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
            "operation": operation,
            "gene": gene,
            "gene_name": gene_name,
            "max_results": max_results,
            "genome_build": genome_build,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "COSMIC_get_mutations_by_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["COSMIC_get_mutations_by_gene"]
