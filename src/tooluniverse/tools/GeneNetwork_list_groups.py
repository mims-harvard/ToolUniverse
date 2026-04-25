"""
GeneNetwork_list_groups

List genetic cross populations (groups) available in GeneNetwork for a given species. These group...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GeneNetwork_list_groups(
    species: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List genetic cross populations (groups) available in GeneNetwork for a given species. These group...

    Parameters
    ----------
    species : str
        Species short name (e.g., 'mouse', 'rat', 'human', 'arabidopsis'). Get from G...
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
    _args = {k: v for k, v in {
        "species": species
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "GeneNetwork_list_groups",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["GeneNetwork_list_groups"]
