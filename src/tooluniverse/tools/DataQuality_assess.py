"""
DataQuality_assess

Assess the quality of a tabular dataset (CSV file or JSON array of records). Returns per-column s...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DataQuality_assess(
    data: list[Any] | str,
    columns: Optional[list[str]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Assess the quality of a tabular dataset (CSV file or JSON array of records). Returns per-column s...

    Parameters
    ----------
    data : list[Any] | str
        Input dataset: either a JSON array of records (list of dicts) or an absolute ...
    columns : list[str]
        List of column names to assess. Default: all columns.
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
    _args = {
        k: v for k, v in {"data": data, "columns": columns}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DataQuality_assess",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DataQuality_assess"]
