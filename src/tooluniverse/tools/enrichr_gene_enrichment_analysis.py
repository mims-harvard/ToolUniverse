"""
enrichr_gene_enrichment_analysis

Perform gene enrichment analysis using Enrichr to find biological pathways, processes, and molecu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def enrichr_gene_enrichment_analysis(
    gene_list: list[str],
    libs: Optional[list[str]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> str:
    """
    Perform gene enrichment analysis using Enrichr to find biological pathways, processes, and molecu...

    Parameters
    ----------
    gene_list : list[str]
        List of gene names or symbols to analyze. At least 2 genes are required for p...
    libs : list[str]
        List of enrichment libraries to use for analysis.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    str
    """
    # Handle mutable defaults to avoid B006 linting error
    if libs is None:
        libs = [
            "WikiPathways_2024_Human",
            "Reactome_Pathways_2024",
            "MSigDB_Hallmark_2020",
            "GO_Molecular_Function_2023",
            "GO_Biological_Process_2023",
        ]
    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v for k, v in {"gene_list": gene_list, "libs": libs}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "enrichr_gene_enrichment_analysis",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["enrichr_gene_enrichment_analysis"]
