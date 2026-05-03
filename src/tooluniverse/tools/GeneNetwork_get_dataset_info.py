"""
GeneNetwork_get_dataset_info

Get metadata about a specific GeneNetwork dataset including its full name, data type, data scale,...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GeneNetwork_get_dataset_info(
    dataset_name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get metadata about a specific GeneNetwork dataset including its full name, data type, data scale,...

    Parameters
    ----------
    dataset_name : str
        Dataset name/abbreviation. Examples: 'HC_M2_0606_P' (Hippocampus Consortium M...
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
    _args = {k: v for k, v in {"dataset_name": dataset_name}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "GeneNetwork_get_dataset_info",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GeneNetwork_get_dataset_info"]
