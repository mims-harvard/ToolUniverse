"""
ModelDB_get_model

Get detailed information about a specific computational neuroscience model from ModelDB by its nu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ModelDB_get_model(
    model_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a specific computational neuroscience model from ModelDB by its nu...

    Parameters
    ----------
    model_id : int
        Numeric model ID from ModelDB. Examples: 3263 (CA3 pyramidal neuron), 2487 (P...
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

    return get_shared_client().run_one_function(
        {"name": "ModelDB_get_model", "arguments": {"model_id": model_id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ModelDB_get_model"]
