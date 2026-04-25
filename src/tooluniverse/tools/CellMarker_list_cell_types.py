"""
CellMarker_list_cell_types

List available cell types in the CellMarker 2.0 database for a given tissue and species. Returns ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CellMarker_list_cell_types(
    operation: str,
    tissue_type: Optional[str] = None,
    species: Optional[str] = None,
    cell_class: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    List available cell types in the CellMarker 2.0 database for a given tissue and species. Returns ...

    Parameters
    ----------
    operation : str
        Operation type
    tissue_type : str
        Tissue type to list cell types for (e.g., 'Blood', 'Lung', 'Brain', 'Liver')....
    species : str
        Species to query (default: 'Human')
    cell_class : str
        Cell class filter: 'all' for normal+cancer (default), 'cancer' for cancer cel...
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
                "tissue_type": tissue_type,
                "species": species,
                "cell_class": cell_class
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "CellMarker_list_cell_types",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["CellMarker_list_cell_types"]
