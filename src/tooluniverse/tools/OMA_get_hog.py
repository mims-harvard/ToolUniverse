"""
OMA_get_hog

Get Hierarchical Orthologous Group (HOG) information from OMA. HOGs represent groups of genes tha...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OMA_get_hog(
    hog_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get Hierarchical Orthologous Group (HOG) information from OMA. HOGs represent groups of genes tha...

    Parameters
    ----------
    hog_id : str
        Hierarchical Orthologous Group ID. Examples: 'HOG:E0739094' (p53 family), 'HO...
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
    _args = {k: v for k, v in {"hog_id": hog_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OMA_get_hog",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OMA_get_hog"]
