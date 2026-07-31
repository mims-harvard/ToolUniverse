"""
BiGG_download_model

Download a complete FBA-ready COBRA metabolic model from BiGG. Unlike BiGG_get_model (which retur...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BiGG_download_model(
    operation: str,
    model_id: str,
    format: Optional[str] = "json",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Download a complete FBA-ready COBRA metabolic model from BiGG. Unlike BiGG_get_model (which retur...

    Parameters
    ----------
    operation : str
        Operation type
    model_id : str
        Required: BiGG model ID (e.g., 'e_coli_core', 'iJO1366', 'iMM904', 'Recon3D')...
    format : str
        Model file format. 'json' (default) returns the parsed COBRA JSON model dict;...
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
        for k, v in {
            "operation": operation,
            "model_id": model_id,
            "format": format,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BiGG_download_model",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BiGG_download_model"]
