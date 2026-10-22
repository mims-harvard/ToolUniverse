"""
Pharos_get_disease_targets

Get Pharos targets associated with a disease, with a real optional TDL facet filter. Pharos curre...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Pharos_get_disease_targets(
    disease: str,
    tdl: Optional[str] = None,
    top: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get Pharos targets associated with a disease, with a real optional TDL facet filter. Pharos curre...

    Parameters
    ----------
    disease : str
        Disease name (e.g., 'breast cancer', 'Alzheimer disease', 'diabetes mellitus')
    tdl : str
        Optional filter by Target Development Level
    top : int
        Number of records to return from Pharos' fixed first-10 ranked window (1-10).
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
        for k, v in {"disease": disease, "tdl": tdl, "top": top}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Pharos_get_disease_targets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Pharos_get_disease_targets"]
