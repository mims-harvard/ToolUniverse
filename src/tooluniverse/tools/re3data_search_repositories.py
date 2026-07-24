"""
re3data_search_repositories

Search re3data.org for research data repositories worldwide. re3data is a global registry of 3,00...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def re3data_search_repositories(
    query: str,
    subjects: Optional[str] = None,
    countries: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search re3data.org for research data repositories worldwide. re3data is a global registry of 3,00...

    Parameters
    ----------
    query : str
        Search keyword(s) to find repositories (e.g., 'nutrition longitudinal', 'geno...
    subjects : str
        Optional subject filter to narrow results (e.g., 'medicine', 'biology', 'chem...
    countries : str
        Optional country filter using ISO 3166 country code (e.g., 'USA', 'GBR', 'DEU...
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
    _args = {
        k: v
        for k, v in {
            "query": query,
            "subjects": subjects,
            "countries": countries,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "re3data_search_repositories",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["re3data_search_repositories"]
