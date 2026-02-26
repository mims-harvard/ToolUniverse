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

    return get_shared_client().run_one_function(
        {
            "name": "Mcule_list_databases",
            "arguments": {"operation": operation, "public_only": public_only},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Mcule_list_databases"]
