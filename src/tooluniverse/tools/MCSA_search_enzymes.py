"""
MCSA_search_enzymes

Search M-CSA for enzymes by name, EC number prefix, or reference UniProt accession. Example: ec_n...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MCSA_search_enzymes(
    enzyme_name: Optional[str] = None,
    ec_number: Optional[str] = None,
    uniprot_id: Optional[str] = None,
    max_pages: Optional[int] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search M-CSA for enzymes by name, EC number prefix, or reference UniProt accession. Example: ec_n...

    Parameters
    ----------
    enzyme_name : str
        Substring of the enzyme name, e.g. 'lysozyme'.
    ec_number : str
        EC number or prefix, e.g. '3.5.2' or '3.5.2.6'.
    uniprot_id : str
        Reference UniProt accession, e.g. 'P62593'.
    max_pages : int
        Catalogue pages to scan, 100 entries each (default 4, max 11 which is the ful...
    limit : int
        Maximum matches to return (default 25).
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
            "enzyme_name": enzyme_name,
            "ec_number": ec_number,
            "uniprot_id": uniprot_id,
            "max_pages": max_pages,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MCSA_search_enzymes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MCSA_search_enzymes"]
