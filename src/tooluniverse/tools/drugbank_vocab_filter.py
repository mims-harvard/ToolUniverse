"""
drugbank_vocab_filter

Filter the DrugBank vocabulary dataset based on specific field criteria. Use simple field-value p...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def drugbank_vocab_filter(
    field: str,
    condition: str,
    limit: int,
    value: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Filter the DrugBank vocabulary dataset based on specific field criteria. Use simple field-value p...

    Parameters
    ----------
    field : str
        The field to filter on
    condition : str
        The type of filtering condition to apply. Filter is case-insensitive.
    value : str
        The value to filter by. Not required when condition is 'not_empty'. Examples:...
    limit : int
        Maximum number of results to return.
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
            "condition": condition,
            "value": value,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "drugbank_vocab_filter",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["drugbank_vocab_filter"]
