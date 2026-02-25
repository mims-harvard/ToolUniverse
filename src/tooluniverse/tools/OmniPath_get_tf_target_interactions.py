"""
OmniPath_get_tf_target_interactions

Get transcription factor (TF) to target gene interactions from OmniPath DoRothEA and CollecTRI re...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OmniPath_get_tf_target_interactions(
    tf_gene: Optional[str | Any] = None,
    target_gene: Optional[str | Any] = None,
    confidence_level: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get transcription factor (TF) to target gene interactions from OmniPath DoRothEA and CollecTRI re...

    Parameters
    ----------
    tf_gene : str | Any
        Transcription factor gene symbol (e.g., 'TP53', 'MYC', 'STAT3'). Mutually exc...
    target_gene : str | Any
        Target gene symbol to find regulating TFs (e.g., 'CDKN1A', 'BCL2'). Mutually ...
    confidence_level : str | Any
        DoRothEA confidence level filter: A=highest (1-2 sources), B=high (3+ sources...
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
        {
            "name": "OmniPath_get_tf_target_interactions",
            "arguments": {
                "tf_gene": tf_gene,
                "target_gene": target_gene,
                "confidence_level": confidence_level,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OmniPath_get_tf_target_interactions"]
