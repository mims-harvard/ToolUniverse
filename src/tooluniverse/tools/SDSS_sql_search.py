"""
SDSS_sql_search

Query the Sloan Digital Sky Survey (SDSS) Data Release 18 database using SQL. SDSS is one of the ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SDSS_sql_search(
    cmd: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Query the Sloan Digital Sky Survey (SDSS) Data Release 18 database using SQL. SDSS is one of the ...

    Parameters
    ----------
    cmd : str
        SQL query against the SDSS DR18 database. Examples: 'SELECT TOP 10 objid,ra,d...
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
    _args = {k: v for k, v in {
        "cmd": cmd
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "SDSS_sql_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["SDSS_sql_search"]
