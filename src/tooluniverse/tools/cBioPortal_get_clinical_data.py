"""
cBioPortal_get_clinical_data

Get clinical data for all samples in a study. Returns patient-level data like tumor stage, histol...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def cBioPortal_get_clinical_data(
    study_id: str,
    clinical_attribute_id: Optional[str] = None,
    page_size: Optional[int] = 100,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get clinical data for all samples in a study. Returns patient-level data like tumor stage, histol...

    Parameters
    ----------
    study_id : str
        Cancer study ID
    clinical_attribute_id : str
        Optional clinical attribute ID to filter by
    page_size : int
        Number of records to return
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
    _args = {
        k: v
        for k, v in {
            "study_id": study_id,
            "clinical_attribute_id": clinical_attribute_id,
            "page_size": page_size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "cBioPortal_get_clinical_data",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["cBioPortal_get_clinical_data"]
