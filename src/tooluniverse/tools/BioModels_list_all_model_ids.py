"""
BioModels_list_all_model_ids

Enumerate ALL BioModels model identifiers - the complete registry of curated (BIOMD...) and non-c...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioModels_list_all_model_ids(
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Enumerate ALL BioModels model identifiers - the complete registry of curated (BIOMD...) and non-c...

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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "BioModels_list_all_model_ids",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioModels_list_all_model_ids"]
