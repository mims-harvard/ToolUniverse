"""
MetaboAnalyst_pathway_enrichment

Perform metabolite pathway enrichment analysis (over-representation analysis) using hypergeometri...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MetaboAnalyst_pathway_enrichment(
    metabolites: list[str],
    organism: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Perform metabolite pathway enrichment analysis (over-representation analysis) using hypergeometri...

    Parameters
    ----------
    metabolites : list[str]
        List of metabolite names to test for pathway enrichment. Example: ['glucose',...
    organism : str
        KEGG organism code. Default 'hsa' (human). Common: hsa=human, mmu=mouse, rno=...
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"metabolites": metabolites, "organism": organism}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MetaboAnalyst_pathway_enrichment",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MetaboAnalyst_pathway_enrichment"]
