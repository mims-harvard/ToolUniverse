"""
CellMarker_search_by_cell_type

Search the CellMarker 2.0 database for marker genes of a specific cell type. Returns curated list...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CellMarker_search_by_cell_type(
    operation: str,
    cell_name: str,
    species: Optional[str] = None,
    tissue_type: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search the CellMarker 2.0 database for marker genes of a specific cell type. Returns curated list...

    Parameters
    ----------
    operation : str
        Operation type
    cell_name : str
        Cell type name to search for (e.g., 'T cell', 'Macrophage', 'B cell', 'Fibrob...
    species : str
        Species filter. If omitted, searches both species.
    tissue_type : str
        Filter results by tissue type (e.g., 'Blood', 'Lung', 'Brain'). Case-insensit...
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
                "cell_name": cell_name,
                "species": species,
                "tissue_type": tissue_type
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "CellMarker_search_by_cell_type",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["CellMarker_search_by_cell_type"]
