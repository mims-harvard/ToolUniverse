"""
cdc_data_aggregate

Run server-side SoQL aggregation on a CDC Data.CDC.gov (Socrata) dataset using the /resource/{dat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def cdc_data_aggregate(
    dataset_id: str,
    select_clause: Optional[str] = None,
    group_clause: Optional[str] = None,
    where_clause: Optional[str] = None,
    having_clause: Optional[str] = None,
    order_by: Optional[str] = None,
    soql_query: Optional[str] = None,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Run server-side SoQL aggregation on a CDC Data.CDC.gov (Socrata) dataset using the /resource/{dat...

    Parameters
    ----------
    dataset_id : str
        Dataset ID (Socrata 4x4 resource id) from Data.CDC.gov, e.g. 'jkcx-ndu8' (wee...
    select_clause : str
        SoQL $select expression, typically grouping columns plus an aggregate functio...
    group_clause : str
        SoQL $group expression: comma-separated non-aggregate columns in select_claus...
    where_clause : str
        Optional SoQL $where filter applied before aggregation. Example: "year = '201...
    having_clause : str
        Optional SoQL $having filter applied to aggregated groups. Example: 'count(*)...
    order_by : str
        Optional SoQL $order expression. Example: 'count_1 DESC', 'event ASC'.
    soql_query : str
        Optional full SoQL query string. When provided it OVERRIDES select_clause/whe...
    limit : int
        Maximum number of grouped result rows to return (default 50, max 50000). Igno...
    offset : int
        Number of result rows to skip for pagination (default 0). Ignored when soql_q...
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
        k: v
        for k, v in {
            "dataset_id": dataset_id,
            "select_clause": select_clause,
            "group_clause": group_clause,
            "where_clause": where_clause,
            "having_clause": having_clause,
            "order_by": order_by,
            "soql_query": soql_query,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "cdc_data_aggregate",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["cdc_data_aggregate"]
