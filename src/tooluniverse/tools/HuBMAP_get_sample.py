"""
HuBMAP_get_sample

Get the full record for a single HuBMAP tissue Sample by its HuBMAP ID, including its CCF/RUI spa...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HuBMAP_get_sample(
    hubmap_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the full record for a single HuBMAP tissue Sample by its HuBMAP ID, including its CCF/RUI spa...

    Parameters
    ----------
    hubmap_id : str
        HuBMAP Sample identifier (e.g. 'HBM658.BXNB.873'). Obtain from HuBMAP_search_...
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
    _args = {k: v for k, v in {"hubmap_id": hubmap_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "HuBMAP_get_sample",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HuBMAP_get_sample"]
