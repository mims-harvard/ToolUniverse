"""
ExpressionAtlas_get_baseline

List baseline gene expression experiments in EBI Expression Atlas for a given species. The `gene`...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ExpressionAtlas_get_baseline(
    gene: str,
    species: Optional[str] = "homo sapiens",
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List baseline gene expression experiments in EBI Expression Atlas for a given species. The `gene`...

    Parameters
    ----------
    gene : str
        Gene symbol (e.g., 'TP53', 'WDR7') or Ensembl ID (e.g., 'ENSG00000141510')
    species : str
        Species name (default: 'homo sapiens'). Also supports 'mus musculus', 'rattus...
    limit : int
        Maximum number of experiments to return (default 50, max 500). Compare with t...
    offset : int
        Zero-based index of the first experiment to return, for paging through result...
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
        for k, v in {
            "gene": gene,
            "species": species,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ExpressionAtlas_get_baseline",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ExpressionAtlas_get_baseline"]
