"""
GWAS_search_associations_by_gene

Search GWAS Catalog associations by gene name with zero-based pagination. Results within each pag...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GWAS_search_associations_by_gene(
    gene_name: str,
    size: Optional[int] = 100,
    page: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search GWAS Catalog associations by gene name with zero-based pagination. Results within each pag...

    Parameters
    ----------
    gene_name : str
        Gene symbol (e.g., BRCA1).
    size : int
        Associations per page (default 100, max 1000). Results are sorted by p-value ...
    page : int
        Zero-based GWAS Catalog result page. Continue with next_page while has_more i...
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
        for k, v in {"gene_name": gene_name, "size": size, "page": page}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GWAS_search_associations_by_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GWAS_search_associations_by_gene"]
