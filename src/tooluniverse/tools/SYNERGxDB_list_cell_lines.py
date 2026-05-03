"""
SYNERGxDB_list_cell_lines

List all cancer cell lines in the SYNERGxDB database. Returns cell line names, tissue types, dise...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SYNERGxDB_list_cell_lines(
    operation: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    List all cancer cell lines in the SYNERGxDB database. Returns cell line names, tissue types, dise...

    Parameters
    ----------
    operation : str
        Operation type
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
    _args = {k: v for k, v in {"operation": operation}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "SYNERGxDB_list_cell_lines",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SYNERGxDB_list_cell_lines"]
