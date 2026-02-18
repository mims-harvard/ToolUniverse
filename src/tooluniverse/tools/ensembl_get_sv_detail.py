"""
ensembl_get_sv_detail

Get detailed information for a specific structural variant from Ensembl by its accession (nsv/esv...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ensembl_get_sv_detail(
    species: str,
    id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information for a specific structural variant from Ensembl by its accession (nsv/esv...

    Parameters
    ----------
    species : str
        Species name (e.g., 'human', 'homo_sapiens').
    id : str
        Structural variant accession from Ensembl/DGVa (e.g., 'nsv2769779', 'esv36474...
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

    return get_shared_client().run_one_function(
        {"name": "ensembl_get_sv_detail", "arguments": {"species": species, "id": id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ensembl_get_sv_detail"]
