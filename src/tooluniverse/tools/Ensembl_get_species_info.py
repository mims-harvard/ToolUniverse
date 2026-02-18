"""
Ensembl_get_species_info

Search and list species available in the Ensembl database with their genome assembly information....
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Ensembl_get_species_info(
    search: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search and list species available in the Ensembl database with their genome assembly information....

    Parameters
    ----------
    search : str
        Search term to filter species. Can be a species name ('mus_musculus'), common...
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
        {"name": "Ensembl_get_species_info", "arguments": {"search": search}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Ensembl_get_species_info"]
