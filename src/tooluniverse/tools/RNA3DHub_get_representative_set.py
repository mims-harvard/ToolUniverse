"""
RNA3DHub_get_representative_set

Get the representative (non-redundant) set of RNA 3D structures from the BGSU RNA 3D Hub. Each we...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RNA3DHub_get_representative_set(
    resolution: Optional[str] = None,
    release: Optional[str] = None,
    pdb_id: Optional[str] = None,
    include_members: Optional[bool] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any] | dict[str, Any]:
    """
    Get the representative (non-redundant) set of RNA 3D structures from the BGSU RNA 3D Hub. Each we...

    Parameters
    ----------
    resolution : str
        Resolution cutoff in angstrom: '1.5', '2.0', '2.5', '3.0', '3.5', '4.0' (defa...
    release : str
        Representative-set release id, e.g. '4.66'. Default 'current' (a new release ...
    pdb_id : str
        Keep only the classes that hold a chain of this PDB entry, e.g. '4TNA'. Each ...
    include_members : bool
        Add the full member list of each class (default false; a ribosomal RNA class ...
    limit : int
        Rows per page (default 50, maximum 500).
    offset : int
        Rows to skip (default 0). Continue with metadata.next_offset while metadata.h...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any] | dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "resolution": resolution,
            "release": release,
            "pdb_id": pdb_id,
            "include_members": include_members,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RNA3DHub_get_representative_set",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RNA3DHub_get_representative_set"]
