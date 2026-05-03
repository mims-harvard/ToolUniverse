"""
MedGen_get_clinical_features

Get HPO clinical features (phenotypes) associated with a genetic condition from NCBI MedGen. Retu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MedGen_get_clinical_features(
    uid: Optional[str] = None,
    cui: Optional[str] = None,
    concept_id: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get HPO clinical features (phenotypes) associated with a genetic condition from NCBI MedGen. Retu...

    Parameters
    ----------
    uid : str
        MedGen UID (e.g., '41393' for cystic fibrosis).
    cui : str
        UMLS CUI (e.g., 'C0010674' for cystic fibrosis). Alternative to uid.
    concept_id : str | Any
        Alias for cui. UMLS CUI identifier (e.g., "C0017205" for Gaucher disease).
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
        for k, v in {"uid": uid, "cui": cui, "concept_id": concept_id}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MedGen_get_clinical_features",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MedGen_get_clinical_features"]
