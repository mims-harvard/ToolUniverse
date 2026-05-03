"""
GO_get_term_by_id

Retrieves basic GO term information by ID using GOlr search.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GO_get_term_by_id(
    id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieves basic GO term information by ID using GOlr search.

    Parameters
    ----------
    id : str
        The standard GO term ID, e.g., 'GO:0006915' for apoptotic process.
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
    _args = {k: v for k, v in {"id": id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "GO_get_term_by_id",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GO_get_term_by_id"]
