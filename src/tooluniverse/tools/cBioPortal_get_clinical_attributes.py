"""
cBioPortal_get_clinical_attributes

Get available clinical attributes for a cancer study. Returns attribute IDs, names, and data type...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def cBioPortal_get_clinical_attributes(
    study_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get available clinical attributes for a cancer study. Returns attribute IDs, names, and data type...

    Parameters
    ----------
    study_id : str
        Cancer study ID (e.g., 'brca_tcga')
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"study_id": study_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "cBioPortal_get_clinical_attributes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["cBioPortal_get_clinical_attributes"]
