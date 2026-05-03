"""
NeuroMorpho_get_field_values

Get available values for a neuron metadata field in NeuroMorpho.Org. Useful for discovering what ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NeuroMorpho_get_field_values(
    field_name: str,
    page: Optional[int] = 0,
    size: Optional[int] = 500,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get available values for a neuron metadata field in NeuroMorpho.Org. Useful for discovering what ...

    Parameters
    ----------
    field_name : str
        Metadata field name. Common fields: 'species', 'brain_region', 'cell_type', '...
    page : int
        Page number (0-indexed). Default: 0.
    size : int
        Results per page (max 500). Default: 500.
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
    _args = {
        k: v
        for k, v in {"field_name": field_name, "page": page, "size": size}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NeuroMorpho_get_field_values",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NeuroMorpho_get_field_values"]
