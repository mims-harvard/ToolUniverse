"""
miRBase_search_mirna

Search for microRNAs (miRNAs) by name, accession, or keyword using EBI Search over RNAcentral. RN...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def miRBase_search_mirna(
    query: str,
    species: Optional[str] = None,
    size: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for microRNAs (miRNAs) by name, accession, or keyword using EBI Search over RNAcentral. RN...

    Parameters
    ----------
    query : str
        Search query: miRNA name (e.g., 'hsa-miR-21-5p'), miRBase accession (e.g., 'M...
    species : str
        Species name filter (e.g., 'Homo sapiens', 'Mus musculus', 'Drosophila melano...
    size : int
        Number of results to return (1-100). Default: 10.
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
        for k, v in {"query": query, "species": species, "size": size}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "miRBase_search_mirna",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["miRBase_search_mirna"]
