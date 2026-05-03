"""
GlyGen_search_glycoproteins

Search GlyGen for glycoproteins by organism, glycosylation evidence type, protein name, or gene n...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GlyGen_search_glycoproteins(
    organism_id: Optional[int] = None,
    glycosylation_evidence: Optional[str] = None,
    glycosylation_type: Optional[str] = None,
    protein_name: Optional[str] = None,
    gene_name: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search GlyGen for glycoproteins by organism, glycosylation evidence type, protein name, or gene n...

    Parameters
    ----------
    organism_id : int
        NCBI taxonomy ID. Examples: 9606 (human), 10090 (mouse), 10029 (Chinese hamst...
    glycosylation_evidence : str
        Evidence level filter. Options: 'reported' (experimentally confirmed).
    glycosylation_type : str
        Type of glycosylation. Examples: 'N-linked', 'O-linked'.
    protein_name : str
        Protein name to search. Example: 'transferrin'.
    gene_name : str
        Gene name to search. Example: 'EGFR'.
    limit : int
        Maximum results to return (default 20, max 50).
    offset : int
        Pagination offset (1-indexed, default 1).
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
            "organism_id": organism_id,
            "glycosylation_evidence": glycosylation_evidence,
            "glycosylation_type": glycosylation_type,
            "protein_name": protein_name,
            "gene_name": gene_name,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GlyGen_search_glycoproteins",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GlyGen_search_glycoproteins"]
