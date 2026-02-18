"""
DisGeNET_get_disease_genes

Get all genes associated with a disease from DisGeNET. Returns ranked gene list with association ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DisGeNET_get_disease_genes(
    operation: str,
    disease: str,
    min_score: Optional[float] = None,
    limit: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get all genes associated with a disease from DisGeNET. Returns ranked gene list with association ...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_disease_genes)
    disease : str
        Disease ID (UMLS CUI) or disease name
    min_score : float
        Minimum association score (0-1). Default: no filter
    limit : int
        Maximum genes to return (default: 50)
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
        {
            "name": "DisGeNET_get_disease_genes",
            "arguments": {
                "operation": operation,
                "disease": disease,
                "min_score": min_score,
                "limit": limit,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DisGeNET_get_disease_genes"]
