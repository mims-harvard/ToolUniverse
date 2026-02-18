"""
DisGeNET_get_gda

Get gene-disease associations with filtering. Filter by data source (CURATED, LITERATURE, ANIMAL_...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DisGeNET_get_gda(
    operation: str,
    gene: Optional[str] = None,
    disease: Optional[str] = None,
    source: Optional[str] = None,
    min_score: Optional[float] = None,
    limit: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get gene-disease associations with filtering. Filter by data source (CURATED, LITERATURE, ANIMAL_...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_gda)
    gene : str
        Gene symbol (optional if disease provided)
    disease : str
        Disease ID/UMLS CUI (optional if gene provided)
    source : str
        Data source filter: CURATED, ANIMAL_MODELS, LITERATURE, etc.
    min_score : float
        Minimum GDA score (0-1). Higher = stronger evidence.
    limit : int
        Maximum results (default: 25)
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
            "name": "DisGeNET_get_gda",
            "arguments": {
                "operation": operation,
                "gene": gene,
                "disease": disease,
                "source": source,
                "min_score": min_score,
                "limit": limit,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DisGeNET_get_gda"]
