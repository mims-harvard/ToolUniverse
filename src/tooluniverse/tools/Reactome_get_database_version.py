"""
Reactome_get_database_version

Get the current Reactome Content Service release number for provenance when comparing pathway, re...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Reactome_get_database_version(
    
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get the current Reactome Content Service release number for provenance when comparing pathway, re...

    Parameters
    ----------
    No parameters
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
    _args = {k: v for k, v in {
        
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Reactome_get_database_version",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["Reactome_get_database_version"]
