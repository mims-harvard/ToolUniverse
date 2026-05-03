"""
ChEMBL_get_assay

Get detailed information about an assay by its ChEMBL assay ID. To find an assay ID, use ChEMBL_s...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChEMBL_get_assay(
    assay_chembl_id: str,
    format: Optional[str] = "json",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about an assay by its ChEMBL assay ID. To find an assay ID, use ChEMBL_s...

    Parameters
    ----------
    assay_chembl_id : str
        ChEMBL assay ID, e.g., 'CHEMBL1217641'
    format : str

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
        for k, v in {"assay_chembl_id": assay_chembl_id, "format": format}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChEMBL_get_assay",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChEMBL_get_assay"]
