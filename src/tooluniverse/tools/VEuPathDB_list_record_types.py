"""
VEuPathDB_list_record_types

List all available record types in VEuPathDB (Eukaryotic Pathogen, Vector and Host Informatics Re...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def VEuPathDB_list_record_types(
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List all available record types in VEuPathDB (Eukaryotic Pathogen, Vector and Host Informatics Re...

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
    Any
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "VEuPathDB_list_record_types",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["VEuPathDB_list_record_types"]
