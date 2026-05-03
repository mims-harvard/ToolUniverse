"""
BiGG_get_model

Get detailed information for a specific metabolic model. Returns organism, genome accession, reac...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BiGG_get_model(
    operation: str,
    model_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information for a specific metabolic model. Returns organism, genome accession, reac...

    Parameters
    ----------
    operation : str
        Operation type
    model_id : str
        Required: BiGG model ID (e.g., 'iJO1366', 'iMM904', 'Recon3D')
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
        for k, v in {"operation": operation, "model_id": model_id}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BiGG_get_model",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BiGG_get_model"]
