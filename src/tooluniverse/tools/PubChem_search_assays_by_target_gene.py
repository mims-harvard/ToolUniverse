"""
PubChem_search_assays_by_target_gene

Search bioassays by target gene symbol. Returns AIDs of assays that screen against the specified ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubChem_search_assays_by_target_gene(
    gene_symbol: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search bioassays by target gene symbol. Returns AIDs of assays that screen against the specified ...

    Parameters
    ----------
    gene_symbol : str
        Gene symbol to search (e.g., EGFR, USP2, TP53)
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
    _args = {k: v for k, v in {"gene_symbol": gene_symbol}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PubChem_search_assays_by_target_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubChem_search_assays_by_target_gene"]
