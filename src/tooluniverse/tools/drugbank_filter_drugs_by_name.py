"""
drugbank_filter_drugs_by_name

Filter DrugBank records based on conditions applied to drug names. For example, find drugs whose ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def drugbank_filter_drugs_by_name(
    condition: str,
    value: str,
    limit: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Filter DrugBank records based on conditions applied to drug names. For example, find drugs whose ...

    Parameters
    ----------
    condition : str
        The condition to apply for filtering.
    value : str
        The value to use with the condition (e.g., 'Aspirin' for 'starts_with'). Requ...
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
        for k, v in {"condition": condition, "value": value, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "drugbank_filter_drugs_by_name",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["drugbank_filter_drugs_by_name"]
