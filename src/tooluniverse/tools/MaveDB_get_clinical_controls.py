"""
MaveDB_get_clinical_controls

Get ClinVar clinical-control variants overlapping a MaveDB score set for functional-score calibra...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MaveDB_get_clinical_controls(
    urn: str,
    clinical_significance: Optional[str] = None,
    limit: Optional[int] = 0,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get ClinVar clinical-control variants overlapping a MaveDB score set for functional-score calibra...

    Parameters
    ----------
    urn : str
        MaveDB score set URN (e.g., 'urn:mavedb:00001263-a-2' for BRCA2 SGE). Obtain ...
    clinical_significance : str
        Optional exact-match filter on ClinVar clinical significance (case-insensitiv...
    limit : int
        Maximum clinical controls on this page. Set to 0 or null to return everything...
    offset : int
        Zero-based offset after the optional significance filter. Continue with data....
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
            "urn": urn,
            "clinical_significance": clinical_significance,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MaveDB_get_clinical_controls",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MaveDB_get_clinical_controls"]
