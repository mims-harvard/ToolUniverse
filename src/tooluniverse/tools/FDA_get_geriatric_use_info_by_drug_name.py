"""
FDA_get_geriatric_use_info_by_drug_name

Retrieve information about geriatric use based on the drug name.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FDA_get_geriatric_use_info_by_drug_name(
    drug_name: str,
    limit: Optional[int] = None,
    skip: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve information about geriatric use based on the drug name.

    Parameters
    ----------
    drug_name : str
        The name of the drug.
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
        for k, v in {"drug_name": drug_name, "limit": limit, "skip": skip}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FDA_get_geriatric_use_info_by_drug_name",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FDA_get_geriatric_use_info_by_drug_name"]
