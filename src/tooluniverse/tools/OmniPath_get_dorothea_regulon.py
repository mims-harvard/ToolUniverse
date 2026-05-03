"""
OmniPath_get_dorothea_regulon

Get the complete DoRothEA regulon for a transcription factor from OmniPath. Returns all target ge...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OmniPath_get_dorothea_regulon(
    tf_gene: str,
    confidence_levels: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the complete DoRothEA regulon for a transcription factor from OmniPath. Returns all target ge...

    Parameters
    ----------
    tf_gene : str
        Transcription factor gene symbol (e.g., 'TP53', 'MYC', 'STAT3', 'NF2')
    confidence_levels : str | Any
        Comma-separated DoRothEA confidence levels to include (e.g., 'A,B' for high c...
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
        for k, v in {"tf_gene": tf_gene, "confidence_levels": confidence_levels}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OmniPath_get_dorothea_regulon",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OmniPath_get_dorothea_regulon"]
