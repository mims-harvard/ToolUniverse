"""
GDC_get_clinical_data

Get detailed clinical data for cancer cases from NCI GDC/TCGA. Returns demographics (gender, race...
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
    Get detailed clinical data for cancer cases from NCI GDC/TCGA. Returns demographics (gender, race...

    Parameters
    ----------
    project_id : str
        GDC project identifier (e.g., 'TCGA-BRCA', 'TCGA-LUAD', 'TARGET-AML')
    primary_site : str
        Primary anatomical site (e.g., 'Breast', 'Lung', 'Brain')
    disease_type : str
        Disease type filter (e.g., 'Ductal and Lobular Neoplasms')
    vital_status : str
        Vital status filter: 'Alive' or 'Dead'
    gender : str
        Gender filter: 'female' or 'male'
    size : int
        Number of cases to return (1-100)
    offset : int
        Pagination offset (0-based)
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
        {
            "name": "GDC_get_clinical_data",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GDC_get_clinical_data"]
