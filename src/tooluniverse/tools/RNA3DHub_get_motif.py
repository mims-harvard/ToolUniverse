"""
RNA3DHub_get_motif

Get one motif group of the BGSU RNA 3D Motif Atlas with its loop instances. Each instance is one ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RNA3DHub_get_motif(
    motif_id: str,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get one motif group of the BGSU RNA 3D Motif Atlas with its loop instances. Each instance is one ...

    Parameters
    ----------
    motif_id : str
        Motif group id with its version, e.g. 'HL_27656.2' or 'IL_03350.3'.
    limit : int
        Loop instances per page (default 50, maximum 500).
    offset : int
        Loop instances to skip (default 0). Continue with metadata.next_offset while ...
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
        for k, v in {"motif_id": motif_id, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RNA3DHub_get_motif",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RNA3DHub_get_motif"]
