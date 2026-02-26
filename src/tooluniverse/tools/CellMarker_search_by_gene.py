"""
CellMarker_search_by_gene

Search the CellMarker 2.0 database for cell types that express a given marker gene. Returns curat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CellMarker_search_by_gene(
    operation: str,
    gene_symbol: str,
    species: Optional[str] = None,
    tissue_type: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search the CellMarker 2.0 database for cell types that express a given marker gene. Returns curat...

    Parameters
    ----------
    operation : str
        Operation type
    gene_symbol : str
        Gene symbol to search for (e.g., 'CD3D', 'CD68', 'EPCAM', 'MS4A1')
    species : str
        Species filter: 'Human' or 'Mouse'. If omitted, searches both species.
    tissue_type : str
        Filter results by tissue type (e.g., 'Blood', 'Lung', 'Brain'). Case-insensit...
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
            "name": "CellMarker_search_by_gene",
            "arguments": {
                "operation": operation,
                "gene_symbol": gene_symbol,
                "species": species,
                "tissue_type": tissue_type,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CellMarker_search_by_gene"]
