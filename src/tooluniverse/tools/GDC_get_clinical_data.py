"""
GDC_get_clinical_data

Get detailed clinical data for cancer cases from NCI GDC/TCGA.
Returns demographics, diagnoses, treatments, and survival information.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GDC_get_clinical_data(
    project_id: Optional[str] = None,
    primary_site: Optional[str] = None,
    disease_type: Optional[str] = None,
    vital_status: Optional[str] = None,
    gender: Optional[str] = None,
    size: Optional[int] = 10,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed clinical data for cancer cases from NCI GDC/TCGA.

    Parameters
    ----------
    project_id : str, optional
        GDC project identifier (e.g., 'TCGA-BRCA', 'TCGA-LUAD').
    primary_site : str, optional
        Primary anatomical site (e.g., 'Breast', 'Lung', 'Brain').
    disease_type : str, optional
        Disease type filter.
    vital_status : str, optional
        Vital status: 'Alive' or 'Dead'.
    gender : str, optional
        Gender: 'female' or 'male'.
    size : int
        Number of cases to return (1-100).
    offset : int
        Pagination offset (0-based).

    Returns
    -------
    dict[str, Any]
    """
    _args = {
        k: v
        for k, v in {
            "project_id": project_id,
            "primary_site": primary_site,
            "disease_type": disease_type,
            "vital_status": vital_status,
            "gender": gender,
            "size": size,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {"name": "GDC_get_clinical_data", "arguments": _args},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GDC_get_clinical_data"]
