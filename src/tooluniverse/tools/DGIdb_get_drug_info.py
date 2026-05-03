"""
DGIdb_get_drug_info

Get basic drug metadata from DGIdb by drug name. Returns drug name, concept ID, and approval stat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DGIdb_get_drug_info(
    drugs: str | list[str],
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get basic drug metadata from DGIdb by drug name. Returns drug name, concept ID, and approval stat...

    Parameters
    ----------
    drugs : str | list[str]
        Drug name(s) to look up. Accepts a single name or a list.
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
    _args = {k: v for k, v in {"drugs": drugs}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "DGIdb_get_drug_info",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DGIdb_get_drug_info"]
