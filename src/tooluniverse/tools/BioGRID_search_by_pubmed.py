"""
BioGRID_search_by_pubmed

Retrieve all protein interactions curated from specific published studies using PubMed ID. Return...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioGRID_search_by_pubmed(
    pubmed_ids: list[str],
    organism: Optional[str] = None,
    interaction_type: Optional[str] = "both",
    include_evidence: Optional[bool] = True,
    limit: Optional[int] = 1000,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve all protein interactions curated from specific published studies using PubMed ID. Return...

    Parameters
    ----------
    pubmed_ids : list[str]
        List of PubMed IDs to query (e.g., ['12345678', '87654321']). Can be numeric ...
    organism : str
        NCBI taxonomy ID to filter interactions by organism (e.g., '9606' for human, ...
    interaction_type : str
        Type of interaction: 'physical', 'genetic', 'both'. Default: 'both'
    include_evidence : bool
        Include detailed evidence information (experimental systems, methods). Defaul...
    limit : int
        Maximum number of interactions to return per publication (default: 1000, max:...
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
            "pubmed_ids": pubmed_ids,
            "organism": organism,
            "interaction_type": interaction_type,
            "include_evidence": include_evidence,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BioGRID_search_by_pubmed",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioGRID_search_by_pubmed"]
