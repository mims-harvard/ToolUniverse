"""
FDA_get_drug_label

Get the complete FDA-approved prescribing information for a specific drug by name. Returns all cl...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FDA_get_drug_label(
    drug_name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the complete FDA-approved prescribing information for a specific drug by name. Returns all cl...

    Parameters
    ----------
    drug_name : str
        Brand or generic drug name (e.g., 'warfarin', 'Eliquis', 'apixaban', 'atorvas...
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
    _args = {k: v for k, v in {"drug_name": drug_name}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "FDA_get_drug_label",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FDA_get_drug_label"]
