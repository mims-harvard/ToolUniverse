"""
CLUE_get_perturbation

Get detailed information about a specific L1000 perturbagen from CLUE.io by ID or name. Returns f...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CLUE_get_perturbation(
    operation: str,
    pert_id: Optional[str | Any] = None,
    pert_iname: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get detailed information about a specific L1000 perturbagen from CLUE.io by ID or name. Returns f...

    Parameters
    ----------
    operation : str
        Operation type
    pert_id : str | Any
        Perturbagen ID (e.g., 'BRD-K12345678'). Mutually exclusive with pert_iname.
    pert_iname : str | Any
        Perturbagen name (e.g., 'imatinib'). Mutually exclusive with pert_id.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "pert_id": pert_id,
            "pert_iname": pert_iname,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CLUE_get_perturbation",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CLUE_get_perturbation"]
