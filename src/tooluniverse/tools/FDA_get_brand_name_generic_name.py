"""
FDA_get_brand_name_generic_name

Retrieve the brand name and generic name from generic name or brand name of a drug.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FDA_get_brand_name_generic_name(
    drug_name: str,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve the brand name and generic name from generic name or brand name of a drug.

    Parameters
    ----------
    drug_name : str
        The generic name or the brand name of the drug.
    limit : int
        The number of records to return.
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
        for k, v in {"drug_name": drug_name, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FDA_get_brand_name_generic_name",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FDA_get_brand_name_generic_name"]
