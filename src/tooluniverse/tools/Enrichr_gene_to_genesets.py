"""
Enrichr_gene_to_genesets

Reverse gene-to-geneset membership lookup. Given ONE gene symbol, return every Enrichr term/gene-...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Enrichr_gene_to_genesets(
    gene: str,
    operation: Optional[str] = None,
    include_metadata: Optional[bool] = False,
    max_terms_per_library: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Reverse gene-to-geneset membership lookup. Given ONE gene symbol, return every Enrichr term/gene-...

    Parameters
    ----------
    operation : str
        Operation type (fixed: gene_to_genesets)
    gene : str
        A single official HGNC gene symbol (e.g., 'STAT3', 'BRCA1'). Case-sensitive; ...
    include_metadata : bool
        If true, also return library category/description metadata (Enrichr setup=tru...
    max_terms_per_library : int
        Optional cap on the number of term names returned per library (0 = no cap, re...
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
            "operation": operation,
            "gene": gene,
            "include_metadata": include_metadata,
            "max_terms_per_library": max_terms_per_library,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Enrichr_gene_to_genesets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Enrichr_gene_to_genesets"]
