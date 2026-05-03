"""
CxGDisc_search_datasets

Search CellxGene Discovery single-cell RNA-seq datasets by tissue, disease, organism, or cell typ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CxGDisc_search_datasets(
    tissue: Optional[str] = None,
    disease: Optional[str] = None,
    organism: Optional[str] = None,
    cell_type: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search CellxGene Discovery single-cell RNA-seq datasets by tissue, disease, organism, or cell typ...

    Parameters
    ----------
    tissue : str
        Filter by tissue name (e.g., 'lung', 'brain', 'heart', 'kidney', 'liver'). Ca...
    disease : str
        Filter by disease (e.g., 'cancer', 'COVID', 'Alzheimer', 'normal'). Case-inse...
    organism : str
        Filter by organism (e.g., 'Homo sapiens', 'Mus musculus'). Case-insensitive p...
    cell_type : str
        Filter by cell type (e.g., 'T cell', 'neuron', 'macrophage', 'epithelial'). C...
    limit : int
        Maximum datasets to return (1-100). Default: 20.
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
            "tissue": tissue,
            "disease": disease,
            "organism": organism,
            "cell_type": cell_type,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CxGDisc_search_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CxGDisc_search_datasets"]
