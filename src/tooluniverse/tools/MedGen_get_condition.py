"""
MedGen_get_condition

Get detailed information about a specific genetic condition from NCBI MedGen by UID or UMLS CUI. ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MedGen_get_condition(
    uid: Optional[str] = None,
    cui: Optional[str] = None,
    concept_id: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a specific genetic condition from NCBI MedGen by UID or UMLS CUI. ...

    Parameters
    ----------
    uid : str
        MedGen UID (e.g., '41393' for cystic fibrosis). Get from MedGen_search_condit...
    cui : str
        UMLS Concept Unique Identifier (e.g., 'C0010674' for cystic fibrosis). Altern...
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
            "name": "MedGen_get_condition",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MedGen_get_condition"]
