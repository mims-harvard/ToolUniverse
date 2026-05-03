"""
FDA_retrieve_drug_names_by_patient_medication_info

Retrieve drug names based on patient medication information, which is about safe use of the drug.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FDA_retrieve_drug_names_by_patient_medication_info(
    patient_info: str,
    limit: Optional[int] = None,
    skip: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve drug names based on patient medication information, which is about safe use of the drug.

    Parameters
    ----------
    patient_info : str
        Information or instructions to patients about safe use of the drug product.
    limit : int
        The number of records to return.
    skip : int
        The number of records to skip.
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
        for k, v in {"patient_info": patient_info, "limit": limit, "skip": skip}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FDA_retrieve_drug_names_by_patient_medication_info",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FDA_retrieve_drug_names_by_patient_medication_info"]
