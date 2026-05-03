"""
PyPIPackageInspector

Extracts comprehensive package information from PyPI and GitHub for quality evaluation. Provides ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PyPIPackageInspector(
    package_name: str,
    include_github: Optional[bool] = True,
    include_downloads: Optional[bool] = True,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Extracts comprehensive package information from PyPI and GitHub for quality evaluation. Provides ...

    Parameters
    ----------
    package_name : str
        Name of the Python package to inspect on PyPI (e.g., 'requests', 'numpy', 'pa...
    include_github : bool
        Whether to fetch GitHub repository statistics (stars, forks, issues, last pus...
    include_downloads : bool
        Whether to fetch download statistics from pypistats.org (downloads per day/we...
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
    _args = {
        k: v
        for k, v in {
            "package_name": package_name,
            "include_github": include_github,
            "include_downloads": include_downloads,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PyPIPackageInspector",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PyPIPackageInspector"]
