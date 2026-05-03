"""
BiGG_list_models

Get list of all genome-scale metabolic models in BiGG database (85+ models). Returns model IDs, o...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BiGG_list_models(
    operation: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get list of all genome-scale metabolic models in BiGG database (85+ models). Returns model IDs, o...

    Parameters
    ----------
    operation : str
        Operation type
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
    _args = {k: v for k, v in {"operation": operation}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "BiGG_list_models",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BiGG_list_models"]
