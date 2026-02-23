"""
ClinGen_get_gene_validity

Get all ClinGen gene-disease validity curations. Returns comprehensive list of gene-disease relat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinGen_get_gene_validity(
    gene: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get all ClinGen gene-disease validity curations. Returns comprehensive list of gene-disease relat...

    Parameters
    ----------
    gene : str
        Optional: Filter by gene symbol
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
        {"name": "ClinGen_get_gene_validity", "arguments": {"gene": gene}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinGen_get_gene_validity"]
