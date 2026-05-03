"""
BioModels_download_model

Download a specific file from a BioModels entry or get the download URL for the entire model as a...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioModels_download_model(
    model_id: str,
    filename: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Download a specific file from a BioModels entry or get the download URL for the entire model as a...

    Parameters
    ----------
    model_id : str
        BioModels identifier (e.g., 'BIOMD0000000469'). Find IDs using biomodels_search.
    filename : str
        Optional specific filename to download. If not provided, returns COMBINE arch...
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
        for k, v in {"model_id": model_id, "filename": filename}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BioModels_download_model",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioModels_download_model"]
