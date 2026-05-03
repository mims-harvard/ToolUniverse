"""
TCIA_get_series

Get imaging series from The Cancer Imaging Archive (TCIA). A series is a set of related images fr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TCIA_get_series(
    Collection: Optional[str | Any] = None,
    PatientID: Optional[str | Any] = None,
    StudyInstanceUID: Optional[str | Any] = None,
    Modality: Optional[str | Any] = None,
    BodyPartExamined: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get imaging series from The Cancer Imaging Archive (TCIA). A series is a set of related images fr...

    Parameters
    ----------
    Collection : str | Any
        Collection name (e.g., 'TCGA-GBM', 'LIDC-IDRI', 'TCGA-LUAD')
    PatientID : str | Any
        Patient identifier
    StudyInstanceUID : str | Any
        DICOM Study Instance UID
    Modality : str | Any
        Imaging modality (e.g., 'CT', 'MR', 'PT', 'CR', 'DX')
    BodyPartExamined : str | Any
        Body part examined (e.g., 'CHEST', 'BRAIN', 'ABDOMEN')
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
            "Collection": Collection,
            "PatientID": PatientID,
            "StudyInstanceUID": StudyInstanceUID,
            "Modality": Modality,
            "BodyPartExamined": BodyPartExamined,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "TCIA_get_series",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TCIA_get_series"]
