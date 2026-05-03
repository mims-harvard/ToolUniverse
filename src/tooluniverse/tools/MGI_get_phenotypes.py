"""
MGI_get_phenotypes

Get phenotype annotations for a mouse gene from MGI (Mouse Genome Informatics). Returns Mammalian...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MGI_get_phenotypes(
    gene_id: str,
    limit: Optional[int] = 20,
    page: Optional[int] = 1,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get phenotype annotations for a mouse gene from MGI (Mouse Genome Informatics). Returns Mammalian...

    Parameters
    ----------
    gene_id : str
        MGI gene identifier with 'MGI:' prefix. Examples: 'MGI:98834' (Trp53), 'MGI:1...
    limit : int
        Number of phenotype annotations to return per page (default: 20, max: 100).
    page : int
        Page number for pagination (default: 1).
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
        for k, v in {"gene_id": gene_id, "limit": limit, "page": page}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MGI_get_phenotypes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MGI_get_phenotypes"]
