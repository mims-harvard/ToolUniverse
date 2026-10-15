"""
CMSOpenPayments_search_payments

Search CMS Open Payments (the 'Sunshine Act' database) for payments and transfers of value from d...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CMSOpenPayments_search_payments(
    npi: Optional[str] = None,
    recipient_last_name: Optional[str] = None,
    manufacturer_id: Optional[str] = None,
    manufacturer_name: Optional[str] = None,
    program_year: Optional[int] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search CMS Open Payments (the 'Sunshine Act' database) for payments and transfers of value from d...

    Parameters
    ----------
    npi : str
        Recipient's National Provider Identifier, e.g. '1528271848'. Fast, indexed.
    recipient_last_name : str
        Recipient's exact last name, e.g. 'Smith'. Slow (~25s), not indexed; prefer n...
    manufacturer_id : str
        Manufacturer/GPO's Open Payments id, e.g. '100000010419'. Fast, indexed.
    manufacturer_name : str
        Manufacturer's exact registered name, e.g. 'Phadia US Inc.'. Slow (~25s), not...
    program_year : int
        Program year, 2019-2025. Default 2024.
    limit : int
        Max payment records to return, 1-100. Default 25.
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
            "npi": npi,
            "recipient_last_name": recipient_last_name,
            "manufacturer_id": manufacturer_id,
            "manufacturer_name": manufacturer_name,
            "program_year": program_year,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CMSOpenPayments_search_payments",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CMSOpenPayments_search_payments"]
