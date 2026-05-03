"""
kegg_get_pathway_info

Get detailed pathway information from KEGG by pathway ID. Returns pathway data including genes, c...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def kegg_get_pathway_info(
    pathway_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed pathway information from KEGG by pathway ID. Returns pathway data including genes, c...

    Parameters
    ----------
    pathway_id : str
        KEGG pathway identifier (e.g., 'hsa00010', 'path:hsa00010')
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
    _args = {k: v for k, v in {"pathway_id": pathway_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "kegg_get_pathway_info",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["kegg_get_pathway_info"]
