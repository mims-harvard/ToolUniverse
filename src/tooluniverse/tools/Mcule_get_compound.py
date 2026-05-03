"""
Mcule_get_compound

Get detailed compound information from Mcule by its Mcule ID. Returns SMILES, InChIKey, standard ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Mcule_get_compound(
    operation: str,
    mcule_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed compound information from Mcule by its Mcule ID. Returns SMILES, InChIKey, standard ...

    Parameters
    ----------
    operation : str
        Operation type
    mcule_id : str
        Mcule compound identifier, e.g., MCULE-3199019536 (aspirin), MCULE-9475454445...
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
        for k, v in {"operation": operation, "mcule_id": mcule_id}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Mcule_get_compound",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Mcule_get_compound"]
