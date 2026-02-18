"""
Ensembl_get_assembly_info

Get genome assembly metadata for a species from the Ensembl REST API. Returns assembly name, acce...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Ensembl_get_assembly_info(
    species: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get genome assembly metadata for a species from the Ensembl REST API. Returns assembly name, acce...

    Parameters
    ----------
    species : str
        Ensembl species name (lowercase with underscores). Examples: 'homo_sapiens' (...
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
        {"name": "Ensembl_get_assembly_info", "arguments": {"species": species}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Ensembl_get_assembly_info"]
