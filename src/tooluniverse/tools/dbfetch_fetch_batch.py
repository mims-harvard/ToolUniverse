"""
dbfetch_fetch_batch

Fetch multiple database entries by IDs in batch. Supports comma-separated IDs or list of IDs. Ret...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def dbfetch_fetch_batch(
    db: str,
    ids: str | list[Any],
    format: Optional[str] = "fasta",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> str:
    """
    Fetch multiple database entries by IDs in batch. Supports comma-separated IDs or list of IDs. Ret...

    Parameters
    ----------
    db : str
        Database name
    ids : str | list[Any]
        Comma-separated IDs or list of IDs (e.g., 'P05067,P04637' or ['P05067', 'P046...
    format : str
        Output format (default: 'fasta')
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    str
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"db": db, "ids": ids, "format": format}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "dbfetch_fetch_batch",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["dbfetch_fetch_batch"]
