"""
PubChemBioAssay_search_by_gene

Search for PubChem BioAssays that target a specific gene with recoverable offset pagination. Retu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubChemBioAssay_search_by_gene(
    gene_symbol: str,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for PubChem BioAssays that target a specific gene with recoverable offset pagination. Retu...

    Parameters
    ----------
    gene_symbol : str
        Human gene symbol. Examples: 'TP53' (tumor protein p53), 'EGFR' (epidermal gr...
    limit : int
        Number of assay summaries per page (1-100; default 20).
    offset : int
        Zero-based offset into all assay IDs for the gene. Continue with next_offset ...
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
            "gene_symbol": gene_symbol,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PubChemBioAssay_search_by_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubChemBioAssay_search_by_gene"]
