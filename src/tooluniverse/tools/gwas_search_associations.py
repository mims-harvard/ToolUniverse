"""
gwas_search_associations

Search the GWAS Catalog for genome-wide association study results by keyword. Accepts free-text d...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def gwas_search_associations(
    disease_trait: Optional[str] = None,
    query: Optional[str] = None,
    efo_uri: Optional[str] = None,
    efo_id: Optional[str] = None,
    efo_trait: Optional[str] = None,
    rs_id: Optional[str] = None,
    accession_id: Optional[str] = None,
    p_value: Optional[float] = None,
    p_value_threshold: Optional[float] = None,
    sort: Optional[str] = None,
    direction: Optional[str] = None,
    size: Optional[int] = None,
    page: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search the GWAS Catalog for genome-wide association study results by keyword. Accepts free-text d...

    Parameters
    ----------
    disease_trait : str
        Disease or trait name for text-based search (e.g., 'diabetes', 'coronary arte...
    query : str
        Alias for disease_trait. Disease or trait name (e.g., 'type 2 diabetes'). NOT...
    efo_uri : str
        Full EFO ontology URI (e.g., 'http://www.ebi.ac.uk/efo/EFO_0001645')
    efo_id : str
        EFO/OBA term ID (e.g., 'EFO_0001645', 'OBA_2050062'). Recommended for reliabl...
    efo_trait : str
        Exact EFO trait label (e.g., 'serum alanine aminotransferase amount'). Use wh...
    rs_id : str
        dbSNP rs identifier
    accession_id : str
        Study accession identifier
    p_value : float
        Maximum p-value threshold for filtering (e.g., 5e-8 for genome-wide significa...
    p_value_threshold : float
        Alias for p_value: maximum p-value threshold.
    sort : str
        Sort field (e.g., 'p_value', 'or_value')
    direction : str
        Sort direction ('asc' or 'desc')
    size : int
        Number of results to return
    page : int
        Page number for pagination
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
            "disease_trait": disease_trait,
            "query": query,
            "efo_uri": efo_uri,
            "efo_id": efo_id,
            "efo_trait": efo_trait,
            "rs_id": rs_id,
            "accession_id": accession_id,
            "p_value": p_value,
            "p_value_threshold": p_value_threshold,
            "sort": sort,
            "direction": direction,
            "size": size,
            "page": page,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "gwas_search_associations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["gwas_search_associations"]
