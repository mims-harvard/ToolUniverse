"""
ProteomicsDB_search_proteins

Search ProteomicsDB for proteins by gene symbol, UniProt accession, or protein name. ProteomicsDB...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ProteomicsDB_search_proteins(
    operation: str,
    query: str,
    organism_id: Optional[int] = None,
    max_results: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search ProteomicsDB for proteins by gene symbol, UniProt accession, or protein name. ProteomicsDB...

    Parameters
    ----------
    operation : str
        Operation type
    query : str
        Search term - gene symbol (e.g., 'KRAS', 'TP53'), UniProt ID (e.g., 'P04637')...
    organism_id : int
        NCBI taxonomy ID for organism filter. Default: 9606 (human). Other options: 1...
    max_results : int
        Maximum number of results to return (default: 20, max: 100)
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
        for k, v in {
            "operation": operation,
            "query": query,
            "organism_id": organism_id,
            "max_results": max_results,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ProteomicsDB_search_proteins",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ProteomicsDB_search_proteins"]
