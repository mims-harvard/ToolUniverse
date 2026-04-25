"""
OpenFDA_get_approved_products

Get FDA-approved product details for a drug including all marketed formulations, active ingredien...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenFDA_get_approved_products(
    operation: str,
    drug_name: Optional[str | Any] = None,
    application_number: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get FDA-approved product details for a drug including all marketed formulations, active ingredien...

    Parameters
    ----------
    operation : str
        Operation type
    drug_name : str | Any
        Drug name (brand or generic, e.g., 'atorvastatin', 'Lipitor')
    application_number : str | Any
        FDA application number (e.g., 'NDA020702')
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
    _args = {k: v for k, v in {
        "operation": operation,
                "drug_name": drug_name,
                "application_number": application_number
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OpenFDA_get_approved_products",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["OpenFDA_get_approved_products"]
