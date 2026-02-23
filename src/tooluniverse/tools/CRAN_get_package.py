"""
CRAN_get_package

Get metadata for a CRAN R package from the CRAN database (crandb). Returns package title, version...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CRAN_get_package(
    package: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get metadata for a CRAN R package from the CRAN database (crandb). Returns package title, version...

    Parameters
    ----------
    package : str
        R package name (case-sensitive). Examples: 'ggplot2', 'dplyr', 'Seurat', 'DES...
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
        {"name": "CRAN_get_package", "arguments": {"package": package}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CRAN_get_package"]
