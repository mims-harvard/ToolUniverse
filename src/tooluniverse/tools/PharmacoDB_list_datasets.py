"""
PharmacoDB_list_datasets

List all cancer pharmacogenomics datasets available in PharmacoDB. Returns dataset names and IDs ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PharmacoDB_list_datasets(
    operation: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    List all cancer pharmacogenomics datasets available in PharmacoDB. Returns dataset names and IDs ...

    Parameters
    ----------
    operation : str
        Operation type
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

    return get_shared_client().run_one_function(
        {"name": "PharmacoDB_list_datasets", "arguments": {"operation": operation}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PharmacoDB_list_datasets"]
