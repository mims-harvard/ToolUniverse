"""
MetaCyc_get_pathway

Get metabolic pathway details from MetaCyc by pathway ID. Returns pathway information, URL to pat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MetaCyc_get_pathway(
    pathway_id: str,
    operation: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get metabolic pathway details from MetaCyc by pathway ID. Returns pathway information, URL to pat...

    Parameters
    ----------
    operation : str

    pathway_id : str
        MetaCyc pathway ID (e.g., PWY-5177, GLYCOLYSIS)
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
    _args = {
        k: v
        for k, v in {"operation": operation, "pathway_id": pathway_id}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MetaCyc_get_pathway",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MetaCyc_get_pathway"]
