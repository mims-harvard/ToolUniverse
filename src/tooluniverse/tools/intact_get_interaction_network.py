"""
intact_get_interaction_network

Get interaction network centered on a specific interactor. Uses EBI Search API (IntAct domain) fo...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def intact_get_interaction_network(
    identifier: Optional[str] = None,
    uniprot_id: Optional[str] = None,
    protein_id: Optional[str] = None,
    gene_symbol: Optional[str] = None,
    gene_name: Optional[str] = None,
    depth: Optional[int] = 1,
    limit: Optional[int] = 50,
    size: Optional[int] = 50,
    format: Optional[str] = "json",
    protein_name: Optional[str] = None,
    protein: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get interaction network centered on a specific interactor. Uses EBI Search API (IntAct domain) fo...

    Parameters
    ----------
    identifier : str
        IntAct identifier, UniProt ID, or gene name. Aliases: uniprot_id, protein_id,...
    uniprot_id : str
        Alias for identifier: UniProt accession (e.g., 'P04637').
    protein_id : str
        Alias for identifier: protein identifier.
    gene_symbol : str
        Alias for identifier: gene symbol (e.g., 'BRCA1').
    gene_name : str
        Alias for identifier: gene name.
    depth : int
        Network depth: 1 for direct interactions only, 2 for 2-hop network, etc. (def...
    limit : int
        Maximum number of interactions to return (default: 50, max: 200). Alias: size.
    size : int
        Alias for limit. Maximum number of interactions to return (default: 50).
    format : str

    protein_name : str
        Alias for gene_symbol/identifier. Common protein name (e.g., MDM2, TP53).
    protein : str
        Alias for identifier. Gene symbol or protein name (e.g., 'TP53', 'BRCA1').
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
            "identifier": identifier,
            "uniprot_id": uniprot_id,
            "protein_id": protein_id,
            "gene_symbol": gene_symbol,
            "gene_name": gene_name,
            "depth": depth,
            "limit": limit,
            "size": size,
            "format": format,
            "protein_name": protein_name,
            "protein": protein,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "intact_get_interaction_network",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["intact_get_interaction_network"]
