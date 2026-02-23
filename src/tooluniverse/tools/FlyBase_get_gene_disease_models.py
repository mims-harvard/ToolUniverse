"""
FlyBase_get_gene_disease_models

Get disease models involving a Drosophila gene from the Alliance of Genome Resources. Drosophila ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FlyBase_get_gene_disease_models(
    gene_id: str,
    limit: Optional[int] = None,
    page: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get disease models involving a Drosophila gene from the Alliance of Genome Resources. Drosophila ...

    Parameters
    ----------
    gene_id : str
        FlyBase gene ID with 'FB:' prefix. Examples: 'FB:FBgn0000490' (dpp), 'FB:FBgn...
    limit : int
        Maximum number of disease models to return (1-100). Default: 20.
    page : int
        Page number for pagination. Default: 1.
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
            "name": "FlyBase_get_gene_disease_models",
            "arguments": {"gene_id": gene_id, "limit": limit, "page": page},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FlyBase_get_gene_disease_models"]
