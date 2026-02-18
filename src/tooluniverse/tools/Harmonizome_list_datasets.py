"""
Harmonizome_list_datasets

List all 100+ integrated genomics datasets available in Harmonizome (Ma'ayan Lab). Returns datase...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Harmonizome_list_datasets(
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List all 100+ integrated genomics datasets available in Harmonizome (Ma'ayan Lab). Returns datase...

    Parameters
    ----------
    No parameters
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

    return get_shared_client().run_one_function(
        {"name": "Harmonizome_list_datasets", "arguments": {}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Harmonizome_list_datasets"]
