"""
civic_get_evidence_item

Get one CIViC evidence item by id, with THE ASSERTIONS THAT CITE IT. Returns the evidence level, ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def civic_get_evidence_item(
    evidence_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get one CIViC evidence item by id, with THE ASSERTIONS THAT CITE IT. Returns the evidence level, ...

    Parameters
    ----------
    evidence_id : int
        CIViC evidence item ID (e.g., 116)
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
    _args = {k: v for k, v in {"evidence_id": evidence_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "civic_get_evidence_item",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["civic_get_evidence_item"]
