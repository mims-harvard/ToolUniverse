"""
WikiPathways_get_pathway_metabolites

Get the metabolite/compound participants (wp:Metabolite nodes) of a WikiPathways pathway. Unlike ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def WikiPathways_get_pathway_metabolites(
    pathway_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the metabolite/compound participants (wp:Metabolite nodes) of a WikiPathways pathway. Unlike ...

    Parameters
    ----------
    pathway_id : str
        WikiPathways pathway identifier. Examples: 'WP534' (Glycolysis & Gluconeogene...
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
    _args = {k: v for k, v in {"pathway_id": pathway_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "WikiPathways_get_pathway_metabolites",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["WikiPathways_get_pathway_metabolites"]
