"""
TogoID_list_datasets

List the biological identifier datasets TogoID can convert between (117 types across categories s...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TogoID_list_datasets(
    category: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List the biological identifier datasets TogoID can convert between (117 types across categories s...

    Parameters
    ----------
    category : str
        Optional category filter, e.g. 'Gene', 'Protein', 'Compound', 'Disease', 'Pat...
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
    _args = {k: v for k, v in {"category": category}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "TogoID_list_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TogoID_list_datasets"]
