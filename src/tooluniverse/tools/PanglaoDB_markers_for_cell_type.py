"""
PanglaoDB_markers_for_cell_type

Get curated marker genes for a single-cell type from PanglaoDB (panglaodb.se). Returns marker gen...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PanglaoDB_markers_for_cell_type(
    cell_type: str,
    species: Optional[str] = None,
    organ: Optional[str] = None,
    canonical_only: Optional[bool] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get curated marker genes for a single-cell type from PanglaoDB (panglaodb.se). Returns marker gen...

    Parameters
    ----------
    cell_type : str
        PanglaoDB cell-type label, e.g. 'B cells', 'Hepatocytes', 'T cells'. Case-ins...
    species : str
        Optional species filter: 'human' (Hs) or 'mouse' (Mm). If omitted, returns ma...
    organ : str
        Optional organ filter, e.g. 'Liver', 'Immune system', 'Pancreas'. Case-insens...
    canonical_only : bool
        If true, return only canonical marker genes. Default false.
    limit : int
        Maximum number of marker genes to return. Default 50.
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
            "cell_type": cell_type,
            "species": species,
            "organ": organ,
            "canonical_only": canonical_only,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PanglaoDB_markers_for_cell_type",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PanglaoDB_markers_for_cell_type"]
