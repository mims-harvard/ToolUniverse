"""
Anaconda_search_packages

Search Anaconda.org for conda packages across all channels (conda-forge, bioconda, defaults, etc....
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Anaconda_search_packages(
    name: str,
    type_: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search Anaconda.org for conda packages across all channels (conda-forge, bioconda, defaults, etc....

    Parameters
    ----------
    name : str
        Package name to search for (e.g., 'numpy', 'samtools', 'biopython', 'r-ggplot2')
    type_ : str | Any
        Package type filter: 'conda' (default), 'pypi', or 'standard_python'
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
            "name": "Anaconda_search_packages",
            "arguments": {"name": name, "type": type_},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Anaconda_search_packages"]
