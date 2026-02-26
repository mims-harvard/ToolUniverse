"""
MetaboAnalyst_get_pathway_library

List available KEGG metabolic pathways for a species with compound counts. Returns all pathways w...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MetaboAnalyst_get_pathway_library(
    organism: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    List available KEGG metabolic pathways for a species with compound counts. Returns all pathways w...

    Parameters
    ----------
    organism : str
        KEGG organism code. Default 'hsa' (human). Common codes: hsa=human, mmu=mouse...
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
        {
            "name": "MetaboAnalyst_get_pathway_library",
            "arguments": {"organism": organism},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MetaboAnalyst_get_pathway_library"]
