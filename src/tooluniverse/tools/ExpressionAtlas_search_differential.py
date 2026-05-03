"""
ExpressionAtlas_search_differential

Search for differential expression experiments from EBI Expression Atlas. Find experiments where ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ExpressionAtlas_search_differential(
    gene: Optional[str] = None,
    condition: Optional[str] = None,
    species: Optional[str] = "homo sapiens",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for differential expression experiments from EBI Expression Atlas. Find experiments where ...

    Parameters
    ----------
    gene : str
        Gene symbol or Ensembl ID (e.g., 'TP53', 'ENSG00000141510')
    condition : str
        Condition/disease to filter by (e.g., 'cancer', 'inflammation', 'breast')
    species : str
        Species name (default: 'homo sapiens')
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"gene": gene, "condition": condition, "species": species}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ExpressionAtlas_search_differential",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ExpressionAtlas_search_differential"]
