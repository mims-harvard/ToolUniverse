"""
VDJDB_search_cdr3

Search VDJdb for TCR/BCR CDR3 sequences linked to antigen specificity. Given a CDR3 amino acid se...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def VDJDB_search_cdr3(
    operation: str,
    cdr3: str,
    species: Optional[str | Any] = None,
    gene: Optional[str | Any] = None,
    match_type: Optional[str] = 'exact',
    substitutions: Optional[int | Any] = None,
    insertions: Optional[int | Any] = None,
    deletions: Optional[int | Any] = None,
    page: Optional[int] = 0,
    page_size: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search VDJdb for TCR/BCR CDR3 sequences linked to antigen specificity. Given a CDR3 amino acid se...

    Parameters
    ----------
    operation : str
        Operation type
    cdr3 : str
        CDR3 amino acid sequence to search (e.g., 'CASSIRSSYEQYF', 'CAAAASGGSYIPTF')
    species : str | Any
        Species filter: HomoSapiens, MusMusculus, or MacacaMulatta
    gene : str | Any
        TCR chain filter: TRA (alpha) or TRB (beta)
    match_type : str
        Match type: 'exact' for exact CDR3 match, 'fuzzy' for Levenshtein distance, '...
    substitutions : int | Any
        Max substitutions for fuzzy match (default: 1). Only used with match_type='fu...
    insertions : int | Any
        Max insertions for fuzzy match (default: 1). Only used with match_type='fuzzy'
    deletions : int | Any
        Max deletions for fuzzy match (default: 1). Only used with match_type='fuzzy'
    page : int
        Page number (0-indexed) for paginated results
    page_size : int
        Number of results per page (default: 25, max: 100)
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
    _args = {k: v for k, v in {
        "operation": operation,
                "cdr3": cdr3,
                "species": species,
                "gene": gene,
                "match_type": match_type,
                "substitutions": substitutions,
                "insertions": insertions,
                "deletions": deletions,
                "page": page,
                "page_size": page_size
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "VDJDB_search_cdr3",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["VDJDB_search_cdr3"]
