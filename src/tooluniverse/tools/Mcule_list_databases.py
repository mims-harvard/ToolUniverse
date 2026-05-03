"""
Mcule_list_databases

List available compound database files from Mcule for bulk download. Mcule provides pre-built dat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Mcule_list_databases(
    operation: str,
    public_only: Optional[bool | Any] = True,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    List available compound database files from Mcule for bulk download. Mcule provides pre-built dat...

    Parameters
    ----------
    operation : str
        Operation type
    public_only : bool | Any
        If true (default), only return publicly accessible databases
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
        for k, v in {"operation": operation, "public_only": public_only}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Mcule_list_databases",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Mcule_list_databases"]
