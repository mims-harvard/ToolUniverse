"""
OMA_get_orthologs

Get pairwise orthologs for a protein from the OMA (Orthologous MAtrix) Browser. Returns orthologo...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OMA_get_orthologs(
    protein_id: str,
    rel_type: Optional[str | Any] = None,
    per_page: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get pairwise orthologs for a protein from the OMA (Orthologous MAtrix) Browser. Returns orthologo...

    Parameters
    ----------
    protein_id : str
        UniProt accession (e.g., 'P04637' for human p53) or OMA ID.
    rel_type : str | Any
        Filter by orthology relationship type. Options: '1:1' (one-to-one), '1:n' (on...
    per_page : int | Any
        Number of orthologs to return (default: 20, max: 100).
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
            "protein_id": protein_id,
            "rel_type": rel_type,
            "per_page": per_page,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OMA_get_orthologs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OMA_get_orthologs"]
