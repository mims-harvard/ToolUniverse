"""
GTEx_get_sample_info

Get detailed GTEx sample and subject metadata. Returns sample IDs, tissue types, donor demographi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GTEx_get_sample_info(
    operation: Optional[str] = None,
    sample_id: Optional[list[str]] = None,
    subject_id: Optional[list[str]] = None,
    tissue_site_detail_id: Optional[list[str]] = None,
    sex: Optional[str] = None,
    age_bracket: Optional[list[str]] = None,
    dataset_id: Optional[str] = "gtex_v8",
    page: Optional[int] = 0,
    items_per_page: Optional[int] = 250,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get detailed GTEx sample and subject metadata. Returns sample IDs, tissue types, donor demographi...

    Parameters
    ----------
    operation : str
        Operation type
    sample_id : list[str]
        Optional: GTEx sample IDs
    subject_id : list[str]
        Optional: GTEx subject/donor IDs
    tissue_site_detail_id : list[str]
        Optional: Filter by tissues
    sex : str
        Optional: Filter by donor sex
    age_bracket : list[str]
        Optional: Filter by age brackets
    dataset_id : str

    page : int

    items_per_page : int

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
            "operation": operation,
            "sample_id": sample_id,
            "subject_id": subject_id,
            "tissue_site_detail_id": tissue_site_detail_id,
            "sex": sex,
            "age_bracket": age_bracket,
            "dataset_id": dataset_id,
            "page": page,
            "items_per_page": items_per_page,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GTEx_get_sample_info",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GTEx_get_sample_info"]
