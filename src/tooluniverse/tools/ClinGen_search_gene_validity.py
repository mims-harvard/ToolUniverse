"""
ClinGen_search_gene_validity

Search ClinGen gene-disease validity curations by gene symbol. Returns classification (Definitive...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinGen_search_gene_validity(
    gene: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search ClinGen gene-disease validity curations by gene symbol. Returns classification (Definitive...

    Parameters
    ----------
    gene : str
        Gene symbol to search (e.g., BRCA1, TP53, CFTR)
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    return get_shared_client().run_one_function(
        {"name": "ClinGen_search_gene_validity", "arguments": {"gene": gene}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinGen_search_gene_validity"]
