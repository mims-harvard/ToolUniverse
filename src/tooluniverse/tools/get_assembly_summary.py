"""
get_assembly_summary

Get key assembly composition and symmetry summary for an assembly associated with a PDB entry.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def get_assembly_summary(
    assembly_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get key assembly composition and symmetry summary for an assembly associated with a PDB entry.

    Parameters
    ----------
    assembly_id : str
        Assembly ID in format 'PDBID-assemblyNumber' (e.g., '1A8M-1')
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
    _args = {k: v for k, v in {"assembly_id": assembly_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "get_assembly_summary",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["get_assembly_summary"]
