"""
HOCOMOCO_get_motif

Get detailed information about a specific HOCOMOCO transcription factor binding motif. Returns ge...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HOCOMOCO_get_motif(
    motif_id: str,
    include_pwm: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about a specific HOCOMOCO transcription factor binding motif. Returns ge...

    Parameters
    ----------
    motif_id : str
        HOCOMOCO motif identifier. Format: GENE.COLLECTION.SUBTYPE.SOURCE.QUALITY. Ex...
    include_pwm : bool
        Whether to include the position weight matrix (PWM) in the response. Default:...
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
        for k, v in {"motif_id": motif_id, "include_pwm": include_pwm}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HOCOMOCO_get_motif",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HOCOMOCO_get_motif"]
