"""
MyChem_query_chemicals

Search MyChem.info with explicit offset pagination and pages up to 1000 records. BioThings expose...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MyChem_query_chemicals(
    query: str,
    fields: Optional[
        str
    ] = "drugbank.name,drugbank.drug_interactions,chebi,pubchem.cid,chembl.molecule_chembl_id",
    size: Optional[int] = 10,
    offset: Optional[int] = 0,
    sort: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search MyChem.info with explicit offset pagination and pages up to 1000 records. BioThings expose...

    Parameters
    ----------
    query : str
        Search query. Examples: 'aspirin' (name), 'BSYNRYMUTXBXSQ-UHFFFAOYSA-N' (InCh...
    fields : str
        Comma-separated fields to return. Common: drugbank, chebi, pubchem, chembl, d...
    size : int
        Maximum number of results (1-1000). offset + size may not exceed 10,000.
    offset : int
        Zero-based result offset within BioThings' first-10,000 window. Continue with...
    sort : str
        Optional upstream sort field. Use 'pubchem.cid' for stable exhaustive paginat...
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
            "query": query,
            "fields": fields,
            "size": size,
            "offset": offset,
            "sort": sort,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MyChem_query_chemicals",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MyChem_query_chemicals"]
