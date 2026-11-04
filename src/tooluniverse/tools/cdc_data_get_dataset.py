"""
cdc_data_get_dataset

Retrieve data from a specific CDC dataset on Data.CDC.gov. Requires a dataset ID (view ID) which ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def cdc_data_get_dataset(
    dataset_id: str,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    where_clause: Optional[str] = None,
    order_by: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve data from a specific CDC dataset on Data.CDC.gov. Requires a dataset ID (view ID) which ...

    Parameters
    ----------
    dataset_id : str
        Dataset ID (view ID) from Data.CDC.gov (e.g., 'p5x4-u35c')
    limit : int
        Maximum number of rows to return (default: 100, max: 50000)
    offset : int
        Number of rows to skip for pagination (default: 0)
    where_clause : str
        Optional SoQL WHERE clause for filtering (e.g., "year = '2020'")
    order_by : str
        Optional column name to order by (e.g., 'year')
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
    _args = {
        k: v
        for k, v in {
            "dataset_id": dataset_id,
            "limit": limit,
            "offset": offset,
            "where_clause": where_clause,
            "order_by": order_by,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "cdc_data_get_dataset",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["cdc_data_get_dataset"]
