"""
BiGG_get_metabolite

Get detailed metabolite information including formula, compartments, and database cross-reference...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BiGG_get_metabolite(
    operation: str,
    metabolite_id: str,
    model_id: Optional[str] = "universal",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed metabolite information including formula, compartments, and database cross-reference...

    Parameters
    ----------
    operation : str
        Operation type
    metabolite_id : str
        Required: BiGG metabolite ID (e.g., 'g3p_c' with compartment, or 'g3p' without)
    model_id : str
        Model ID or 'universal' for universal metabolite database
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
            "operation": operation,
            "metabolite_id": metabolite_id,
            "model_id": model_id,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BiGG_get_metabolite",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BiGG_get_metabolite"]
