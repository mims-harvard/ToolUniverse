"""
Orphanet_get_icd_mapping

Get cross-references between Orphanet ORPHA codes and other medical coding systems (ICD-10, ICD-1...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Orphanet_get_icd_mapping(
    operation: Optional[str] = None,
    orpha_code: Optional[str | int] = None,
    coding_system: Optional[str] = "all",
    lang: Optional[str] = "en",
    orphacode: Optional[int | str] = None,
    orpha_id: Optional[int | str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get cross-references between Orphanet ORPHA codes and other medical coding systems (ICD-10, ICD-1...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_icd_mapping)
    orpha_code : str | int
        Orphanet ORPHA code (e.g., 558 for Marfan, 586 for Cystic Fibrosis)
    coding_system : str
        Which coding system to retrieve: all, icd10, icd11, omim, snomed. Default: all
    lang : str
        Language code (default: en)
    orphacode : int | str
        Alias for orpha_code (the Orphanet disease code).
    orpha_id : int | str
        Alias for orpha_code (the Orphanet disease code).
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
            "operation": operation,
            "orpha_code": orpha_code,
            "coding_system": coding_system,
            "lang": lang,
            "orphacode": orphacode,
            "orpha_id": orpha_id,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Orphanet_get_icd_mapping",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Orphanet_get_icd_mapping"]
