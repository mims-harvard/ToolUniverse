"""
CellTypist_get_model

Retrieve metadata for one CellTypist model by filename, including its training description, numbe...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CellTypist_get_model(
    filename: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve metadata for one CellTypist model by filename, including its training description, numbe...

    Parameters
    ----------
    filename : str
        Model filename, e.g. 'Immune_All_Low.pkl'. Case-insensitive.
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
    _args = {k: v for k, v in {"filename": filename}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "CellTypist_get_model",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CellTypist_get_model"]
