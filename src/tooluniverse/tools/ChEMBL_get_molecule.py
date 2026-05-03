"""
ChEMBL_get_molecule

Get detailed information about a molecule by its ChEMBL ID. Returns molecule properties, structur...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChEMBL_get_molecule(
    chembl_id: Optional[str] = None,
    format: Optional[str] = "json",
    molecule_chembl_id: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about a molecule by its ChEMBL ID. Returns molecule properties, structur...

    Parameters
    ----------
    chembl_id : str
        ChEMBL molecule ID, e.g., 'CHEMBL25'
    format : str
        Response format
    molecule_chembl_id : str
        Alias for chembl_id. ChEMBL molecule ID, e.g., CHEMBL1229517.
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
            "chembl_id": chembl_id,
            "format": format,
            "molecule_chembl_id": molecule_chembl_id,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChEMBL_get_molecule",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChEMBL_get_molecule"]
