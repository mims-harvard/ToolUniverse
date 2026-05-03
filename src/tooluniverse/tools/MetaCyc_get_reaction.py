"""
MetaCyc_get_reaction

Get reaction details from MetaCyc by reaction ID. Returns reaction information including substrat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MetaCyc_get_reaction(
    reaction_id: str,
    operation: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get reaction details from MetaCyc by reaction ID. Returns reaction information including substrat...

    Parameters
    ----------
    operation : str

    reaction_id : str
        MetaCyc reaction ID (e.g., RXN-14500)
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
        for k, v in {"operation": operation, "reaction_id": reaction_id}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MetaCyc_get_reaction",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MetaCyc_get_reaction"]
