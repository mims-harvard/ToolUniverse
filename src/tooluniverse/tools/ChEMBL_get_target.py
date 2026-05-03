"""
ChEMBL_get_target

Get detailed information about a target (protein, gene, etc.) by its ChEMBL target ID. To find a ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChEMBL_get_target(
    target_chembl_id: str,
    format: Optional[str] = "json",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about a target (protein, gene, etc.) by its ChEMBL target ID. To find a ...

    Parameters
    ----------
    target_chembl_id : str
        ChEMBL target ID (e.g., 'CHEMBL2074'). To find a target ID, use ChEMBL_search...
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
        for k, v in {"target_chembl_id": target_chembl_id, "format": format}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChEMBL_get_target",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChEMBL_get_target"]
