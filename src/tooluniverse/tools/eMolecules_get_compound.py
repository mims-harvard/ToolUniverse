"""
eMolecules_get_compound

Get compound details by eMolecules ID. Returns a URL linking to the compound page with vendor, pr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def eMolecules_get_compound(
    emol_id: str,
    operation: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get compound details by eMolecules ID. Returns a URL linking to the compound page with vendor, pr...

    Parameters
    ----------
    operation : str

    emol_id : str
        eMolecules compound/vendor ID
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
        for k, v in {"operation": operation, "emol_id": emol_id}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "eMolecules_get_compound",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["eMolecules_get_compound"]
