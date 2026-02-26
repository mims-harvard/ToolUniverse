"""
SYNERGxDB_get_combo_matrix

Get the dose-response matrix data for a specific drug combination experiment in SYNERGxDB. Return...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SYNERGxDB_get_combo_matrix(
    operation: str,
    combo_id: int,
    source_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get the dose-response matrix data for a specific drug combination experiment in SYNERGxDB. Return...

    Parameters
    ----------
    operation : str
        Operation type
    combo_id : int
        Combination design ID from search_combos results (comboId field)
    source_id : int
        Dataset source ID (idSource field from search_combos or list_datasets)
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

    return get_shared_client().run_one_function(
        {
            "name": "SYNERGxDB_get_combo_matrix",
            "arguments": {
                "operation": operation,
                "combo_id": combo_id,
                "source_id": source_id,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SYNERGxDB_get_combo_matrix"]
