"""
RCSBData_get_entry

Get comprehensive structure metadata for a PDB entry from the RCSB Data API. Returns experimental...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RCSBData_get_entry(
    pdb_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get comprehensive structure metadata for a PDB entry from the RCSB Data API. Returns experimental...

    Parameters
    ----------
    pdb_id : str
        PDB entry ID (4 characters). Examples: '4HHB' (hemoglobin), '1TUP' (p53-DNA c...
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
    _args = {k: v for k, v in {"pdb_id": pdb_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "RCSBData_get_entry",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RCSBData_get_entry"]
