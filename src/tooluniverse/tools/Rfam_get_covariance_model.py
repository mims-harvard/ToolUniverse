"""
Rfam_get_covariance_model

Get Infernal covariance model (CM) for RNA family. Returns CM file in Infernal format, which capt...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Rfam_get_covariance_model(
    operation: str,
    family_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get Infernal covariance model (CM) for RNA family. Returns CM file in Infernal format, which capt...

    Parameters
    ----------
    operation : str
        Operation type
    family_id : str
        Required: Rfam accession or family name
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
        for k, v in {"operation": operation, "family_id": family_id}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Rfam_get_covariance_model",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Rfam_get_covariance_model"]
