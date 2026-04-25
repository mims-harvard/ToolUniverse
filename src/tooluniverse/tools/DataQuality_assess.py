"""
DataQuality_assess

Assess the quality of a tabular dataset (CSV file or JSON array of records).
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DataQuality_assess(
    data: list[dict] | str,
    *,
    columns: list[str] | None = None,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Assess the quality of a tabular dataset.

    Parameters
    ----------
    data : list[dict] | str
        JSON array of records (list of dicts) or absolute path to a CSV file.
    columns : list[str] | None, optional
        List of column names to assess. Default: all columns.
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
