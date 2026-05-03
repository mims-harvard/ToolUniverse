"""
Alliance_get_disease_genes

Get genes associated with a disease across all model organisms from the Alliance of Genome Resour...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Alliance_get_disease_genes(
    disease_id: str,
    limit: Optional[int] = None,
    page: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get genes associated with a disease across all model organisms from the Alliance of Genome Resour...

    Parameters
    ----------
    disease_id : str
        Disease Ontology (DO) ID. Examples: 'DOID:162' (cancer), 'DOID:10652' (Alzhei...
    limit : int
        Maximum number of gene associations to return (1-100). Default: 20.
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"disease_id": disease_id, "limit": limit, "page": page}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Alliance_get_disease_genes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Alliance_get_disease_genes"]
