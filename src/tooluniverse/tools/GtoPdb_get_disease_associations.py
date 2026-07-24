"""
GtoPdb_get_disease_associations

Get curated disease-to-target and disease-to-ligand associations from the Guide to Pharmacology (...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GtoPdb_get_disease_associations(
    disease_id: Optional[int] = None,
    diseaseId: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get curated disease-to-target and disease-to-ligand associations from the Guide to Pharmacology (...

    Parameters
    ----------
    disease_id : int
        GtoPdb disease ID. Get from GtoPdb_search_diseases. Examples: 1161 (non-aller...
    diseaseId : int
        Alias for disease_id. GtoPdb disease ID.
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
        for k, v in {"disease_id": disease_id, "diseaseId": diseaseId}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GtoPdb_get_disease_associations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GtoPdb_get_disease_associations"]
