"""
G2P_get_gene

Get Gene2Phenotype information for a specific gene by symbol. Returns gene location, cross-refere...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def G2P_get_gene(
    gene_symbol: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get Gene2Phenotype information for a specific gene by symbol. Returns gene location, cross-refere...

    Parameters
    ----------
    gene_symbol : str
        Gene symbol (e.g., 'BRCA1', 'TP53', 'EGFR', 'SCN1A')
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
    _args = {k: v for k, v in {"gene_symbol": gene_symbol}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "G2P_get_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["G2P_get_gene"]
