"""
Orphanet_get_icd_mapping

Get cross-references between Orphanet ORPHA codes and other medical coding systems (ICD-10, ICD-1...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Orphanet_get_icd_mapping(
    operation: str,
    orpha_code: str,
    coding_system: Optional[str] = "all",
    lang: Optional[str] = "en",
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
    orpha_code : str
        Orphanet ORPHA code (e.g., 558 for Marfan, 586 for Cystic Fibrosis)
    coding_system : str
        Which coding system to retrieve: all, icd10, icd11, omim, snomed. Default: all
    lang : str
        Language code (default: en)
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

    return get_shared_client().run_one_function(
        {
            "name": "Orphanet_get_icd_mapping",
            "arguments": {
                "operation": operation,
                "orpha_code": orpha_code,
                "coding_system": coding_system,
                "lang": lang,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Orphanet_get_icd_mapping"]
