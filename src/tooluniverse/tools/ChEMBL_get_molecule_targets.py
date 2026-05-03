"""
ChEMBL_get_molecule_targets

Get all unique targets associated with a molecule by ChEMBL ID. Returns targets that have activit...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChEMBL_get_molecule_targets(
    molecule_chembl_id__exact: Optional[str] = None,
    molecule_chembl_id: Optional[str] = None,
    limit: Optional[int] = 500,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get all unique targets associated with a molecule by ChEMBL ID. Returns targets that have activit...

    Parameters
    ----------
    molecule_chembl_id__exact : str
        ChEMBL molecule ID (e.g., 'CHEMBL25' for aspirin). To find a molecule ID, use...
    molecule_chembl_id : str
        Alias for molecule_chembl_id__exact. ChEMBL molecule ID.
    limit : int
        Maximum number of activity records to fetch for target deduplication (default...
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
        for k, v in {
            "molecule_chembl_id__exact": molecule_chembl_id__exact,
            "molecule_chembl_id": molecule_chembl_id,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChEMBL_get_molecule_targets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChEMBL_get_molecule_targets"]
