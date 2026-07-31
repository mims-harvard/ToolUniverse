"""
SwissLipids_get_lipid

Retrieve a full SwissLipids entry by its id (e.g. 'SLM:000000510'). Returns the lipid's name, mol...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SwissLipids_get_lipid(
    entity_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve a full SwissLipids entry by its id (e.g. 'SLM:000000510'). Returns the lipid's name, mol...

    Parameters
    ----------
    entity_id : str
        SwissLipids id, e.g. 'SLM:000000510' (a bare number is also accepted).
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
    _args = {k: v for k, v in {"entity_id": entity_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "SwissLipids_get_lipid",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SwissLipids_get_lipid"]
