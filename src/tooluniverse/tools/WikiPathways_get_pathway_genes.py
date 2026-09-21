"""
WikiPathways_get_pathway_genes

Get the genes involved in a WikiPathways pathway. `gene_count` counts distinct gene products; `ge...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def WikiPathways_get_pathway_genes(
    pathway_id: Optional[str] = None,
    wpid: Optional[str] = None,
    code: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the genes involved in a WikiPathways pathway. `gene_count` counts distinct gene products; `ge...

    Parameters
    ----------
    pathway_id : str
        WikiPathways pathway identifier. Examples: 'WP254' (Apoptosis, 87 gene produc...
    wpid : str
        Alias for `pathway_id`, matching the parameter name used by the sibling WikiP...
    code : str
        Optional filter restricting results to gene products annotated from one ident...
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
        for k, v in {"pathway_id": pathway_id, "wpid": wpid, "code": code}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "WikiPathways_get_pathway_genes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["WikiPathways_get_pathway_genes"]
