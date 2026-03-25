"""
KEGG_get_disease

Get detailed KEGG disease information including disease name, category, description, associated g...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def KEGG_get_disease(
    disease_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed KEGG disease information including disease name, category, description, associated g...

    Parameters
    ----------
    disease_id : str
        KEGG disease ID in H##### format (e.g., 'H00001' for B-cell ALL, 'H00408' for...
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
    _args = {k: v for k, v in {"disease_id": disease_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "KEGG_get_disease",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["KEGG_get_disease"]
