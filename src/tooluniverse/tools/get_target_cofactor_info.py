"""
get_target_cofactor_info

Retrieve essential cofactor information for a given target including cofactor IDs, mechanism of a...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def get_target_cofactor_info(
    pdb_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve essential cofactor information for a given target including cofactor IDs, mechanism of a...

    Parameters
    ----------
    pdb_id : str
        Target ID or entity identifier (e.g., UniProt ID or internal target id)
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
    _args = {k: v for k, v in {"pdb_id": pdb_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "get_target_cofactor_info",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["get_target_cofactor_info"]
