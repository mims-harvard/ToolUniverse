"""
COSMIC_get_mutations_by_gene

Retrieve COSMIC mutation records constrained to one gene symbol. Repeated source records are aggr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def COSMIC_get_mutations_by_gene(
    gene: str,
    operation: Optional[str] = "get_by_gene",
    max_results: Optional[int] = 100,
    genome_build: Optional[int] = 37,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve COSMIC mutation records constrained to one gene symbol. Repeated source records are aggr...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_by_gene)
    gene : str
        HGNC-style gene symbol, e.g. BRAF, TP53, HLA-DRA.
    max_results : int
        Maximum unique mutations to return from the accessible 500-source-record wind...
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
