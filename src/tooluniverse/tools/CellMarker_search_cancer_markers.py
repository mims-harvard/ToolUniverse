"""
CellMarker_search_cancer_markers

Search the CellMarker 2.0 database for cancer-specific cell markers. Returns marker genes and cel...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CellMarker_search_cancer_markers(
    operation: str,
    cancer_type: Optional[str] = None,
    gene_symbol: Optional[str] = None,
    cell_type: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search the CellMarker 2.0 database for cancer-specific cell markers. Returns marker genes and cel...

    Parameters
    ----------
    operation : str
        Operation type
    cancer_type : str
        Cancer tissue type (e.g., 'Breast', 'Lung', 'Brain', 'Liver'). Filters by tis...
    gene_symbol : str
        Marker gene to search in cancer context (e.g., 'CD274' for PD-L1, 'EPCAM')
    cell_type : str
        Cancer cell type to search for (e.g., 'Cancer stem cell', 'T cell', 'Macropha...
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
                "cancer_type": cancer_type,
                "gene_symbol": gene_symbol,
                "cell_type": cell_type
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "CellMarker_search_cancer_markers",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["CellMarker_search_cancer_markers"]
