"""
gProfiler_enrichment

Perform functional enrichment analysis on a gene list using g:Profiler (g:GOSt) from the Universi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def gProfiler_enrichment(
    gene_list: str,
    organism: Optional[str] = None,
    sources: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Perform functional enrichment analysis on a gene list using g:Profiler (g:GOSt) from the Universi...

    Parameters
    ----------
    gene_list : str
        Comma-separated list of gene symbols. Examples: 'TP53,BRCA1,EGFR,KRAS,PTEN' o...
    organism : str
        Organism identifier. Default: 'hsapiens'. Examples: 'hsapiens' (human), 'mmus...
    sources : str
        Comma-separated data sources to query. Default: 'GO:BP,GO:MF,GO:CC,KEGG,REAC,...
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
            "gene_list": gene_list,
            "organism": organism,
            "sources": sources,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "gProfiler_enrichment",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["gProfiler_enrichment"]
