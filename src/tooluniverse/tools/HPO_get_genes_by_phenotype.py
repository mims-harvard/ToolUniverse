"""
HPO_get_genes_by_phenotype

Get the genes associated with an HPO phenotype term (genes in which variants cause this phenotype...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HPO_get_genes_by_phenotype(
    term_id: str,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the genes associated with an HPO phenotype term (genes in which variants cause this phenotype...

    Parameters
    ----------
    term_id : str
        HPO term identifier (e.g., 'HP:0001250'). Must start with 'HP:' followed by 7...
    limit : int
        Maximum number of results to return (1-500, default 50). Phenotype terms can ...
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
        k: v for k, v in {"term_id": term_id, "limit": limit}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HPO_get_genes_by_phenotype",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HPO_get_genes_by_phenotype"]
