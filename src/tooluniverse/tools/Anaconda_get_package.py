"""
Anaconda_get_package

Get detailed information about a specific conda package from a specific channel on Anaconda.org. ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Anaconda_get_package(
    channel: str,
    package_name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a specific conda package from a specific channel on Anaconda.org. ...

    Parameters
    ----------
    channel : str
        Channel or owner name (e.g., 'conda-forge', 'bioconda', 'defaults', 'anaconda')
    package_name : str
        Exact package name (e.g., 'numpy', 'samtools', 'biopython', 'r-ggplot2')
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
            "name": "Anaconda_get_package",
            "arguments": {"channel": channel, "package_name": package_name},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Anaconda_get_package"]
