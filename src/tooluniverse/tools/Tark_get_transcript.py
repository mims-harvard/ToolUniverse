"""
Tark_get_transcript

Get the archived transcript record for an Ensembl transcript id (ENST) from the Ensembl Tark tran...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Tark_get_transcript(
    stable_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the archived transcript record for an Ensembl transcript id (ENST) from the Ensembl Tark tran...

    Parameters
    ----------
    stable_id : str
        Ensembl transcript stable id, e.g. 'ENST00000380152' (version optional).
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
    _args = {k: v for k, v in {"stable_id": stable_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Tark_get_transcript",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Tark_get_transcript"]
