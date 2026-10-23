"""
SCREEN_get_regulatory_elements

Resolve an official human gene symbol to its GRCh38 coordinates with Ensembl, then return genuine...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SCREEN_get_regulatory_elements(
    gene_name: Optional[str] = None,
    query: Optional[str] = None,
    element_type: Optional[str] = "enhancer",
    limit: Optional[int] = 10,
    offset: Optional[int] = 0,
    flank_bp: Optional[int] = 10000,
    assembly: Optional[str] = "GRCh38",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Resolve an official human gene symbol to its GRCh38 coordinates with Ensembl, then return genuine...

    Parameters
    ----------
    gene_name : str
        Gene symbol to search for regulatory elements (e.g., BRCA1, TP53). Alias: 'qu...
    query : str
        Gene symbol to search for regulatory elements (alias for gene_name).
    element_type : str
        cCRE class filter: enhancer (pELS+dELS), promoter (PLS), insulator (CTCF-only...
    limit : int
        Page size for filtered cCREs.
    offset : int
        Zero-based filtered cCRE offset. Continue with metadata.next_offset while met...
    flank_bp : int
        Base pairs added on both sides of the Ensembl gene interval (default 10000).
    assembly : str
        Genome assembly. This gene-symbol resolver currently supports human GRCh38 only.
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
            "gene_name": gene_name,
            "query": query,
            "element_type": element_type,
            "limit": limit,
            "offset": offset,
            "flank_bp": flank_bp,
            "assembly": assembly,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SCREEN_get_regulatory_elements",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SCREEN_get_regulatory_elements"]
