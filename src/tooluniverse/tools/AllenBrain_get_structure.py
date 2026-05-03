"""
AllenBrain_get_structure

Get detailed information about a brain structure by its Allen Brain Atlas structure ID. Returns f...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def AllenBrain_get_structure(
    structure_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about a brain structure by its Allen Brain Atlas structure ID. Returns f...

    Parameters
    ----------
    structure_id : int
        Allen Brain Atlas structure ID. Examples: 382 (CA1), 375 (Hippocampus), 315 (...
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
    _args = {k: v for k, v in {"structure_id": structure_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "AllenBrain_get_structure",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["AllenBrain_get_structure"]
