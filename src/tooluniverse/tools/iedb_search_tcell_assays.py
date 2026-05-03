"""
iedb_search_tcell_assays

Search T-cell assay data from the IEDB. Returns T-cell response assays with epitope sequences, MH...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def iedb_search_tcell_assays(
    sequence: Optional[str] = None,
    sequence_contains: Optional[str] = None,
    mhc_class: Optional[str] = None,
    qualitative_measure: Optional[str] = None,
    limit: Optional[int] = 10,
    offset: Optional[int] = 0,
    select: Optional[str | list[str]] = None,
    filters: Optional[dict[str, Any]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search T-cell assay data from the IEDB. Returns T-cell response assays with epitope sequences, MH...

    Parameters
    ----------
    sequence : str
        Exact peptide sequence to search (e.g., GILGFVFTL for influenza M1 epitope).
    sequence_contains : str
        Partial peptide sequence (substring match). Example: 'SIINFEKL'.
    mhc_class : str
        MHC class restriction (I or II).
    qualitative_measure : str
        Filter by assay result.
    limit : int
        Maximum rows to return.
    offset : int
        Pagination offset.
    select : str | list[str]
        Columns to return (array of strings). Example: ['tcell_id','linear_sequence',...
    filters : dict[str, Any]
        Advanced PostgREST filters (e.g., {"source_organism_iri":"eq.NCBITaxon:11320"}).
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "sequence": sequence,
            "sequence_contains": sequence_contains,
            "mhc_class": mhc_class,
            "qualitative_measure": qualitative_measure,
            "limit": limit,
            "offset": offset,
            "select": select,
            "filters": filters,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "iedb_search_tcell_assays",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["iedb_search_tcell_assays"]
