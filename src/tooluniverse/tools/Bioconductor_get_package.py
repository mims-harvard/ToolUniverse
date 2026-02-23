"""
Bioconductor_get_package

Get detailed metadata for a specific Bioconductor R package by name. Returns comprehensive inform...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Bioconductor_get_package(
    package_name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed metadata for a specific Bioconductor R package by name. Returns comprehensive inform...

    Parameters
    ----------
    package_name : str
        Exact Bioconductor package name (case-sensitive). Examples: 'DESeq2', 'edgeR'...
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
        {
            "name": "Bioconductor_get_package",
            "arguments": {"package_name": package_name},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Bioconductor_get_package"]
