"""
FDA_get_drug_label_info_by_field_value

Retrieve FDA drug label information by searching a specific FDA drug label field for a given valu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FDA_get_drug_label_info_by_field_value(
    field: str,
    field_value: str,
    return_fields: Optional[str] = None,
    limit: Optional[int] = None,
    skip: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve FDA drug label information by searching a specific FDA drug label field for a given valu...

    Parameters
    ----------
    field : str
        Which field to search. Choose one value from the Allowed fields list in this ...
    field_value : str
        The value to search for in the specified field (exact match).
    return_fields : str
        Which fields/sections to return. Use "ALL" to return full label records. If o...
    limit : int
        The number of records to return (default: 100).
    skip : int
        The number of records to skip (default: 0).
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
            "field": field,
            "field_value": field_value,
            "return_fields": return_fields,
            "limit": limit,
            "skip": skip,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FDA_get_drug_label_info_by_field_value",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FDA_get_drug_label_info_by_field_value"]
