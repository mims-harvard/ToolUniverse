"""
TCIA_get_patient_studies

Get study information for patients in The Cancer Imaging Archive (TCIA). Returns study metadata i...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TCIA_get_patient_studies(
    Collection: Optional[str | Any] = None,
    PatientID: Optional[str | Any] = None,
    StudyInstanceUID: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get study information for patients in The Cancer Imaging Archive (TCIA). Returns study metadata i...

    Parameters
    ----------
    Collection : str | Any
        Collection name (e.g., 'TCGA-GBM', 'LIDC-IDRI')
    PatientID : str | Any
        Patient identifier
    StudyInstanceUID : str | Any
        DICOM Study Instance UID
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

    return get_shared_client().run_one_function(
        {
            "name": "TCIA_get_patient_studies",
            "arguments": {
                "Collection": Collection,
                "PatientID": PatientID,
                "StudyInstanceUID": StudyInstanceUID,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TCIA_get_patient_studies"]
