"""
FDAPurpleBook_search_products

Search FDA's Purple Book of licensed biological products: reference biologics, their licensed bio...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FDAPurpleBook_search_products(
    proprietary_name: Optional[str] = None,
    proper_name: Optional[str] = None,
    applicant: Optional[str] = None,
    bla_number: Optional[str] = None,
    license_type: Optional[str] = None,
    reference_product_proper_name: Optional[str] = None,
    reference_product_proprietary_name: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search FDA's Purple Book of licensed biological products: reference biologics, their licensed bio...

    Parameters
    ----------
    proprietary_name : str
        Brand name, e.g. 'Humira'.
    proper_name : str
        Non-proprietary/generic name (INN), e.g. 'adalimumab'.
    applicant : str
        License holder, e.g. 'AbbVie'.
    bla_number : str
        Biologics License Application number, e.g. '125057'.
    license_type : str
        '351(a)' (reference biologic), '351(k) Biosimilar', or '351(k) Interchangeable'.
    reference_product_proper_name : str
        For biosimilars/interchangeables: the reference product's generic name they w...
    reference_product_proprietary_name : str
        For biosimilars/interchangeables: the reference product's brand name, e.g. 'H...
    limit : int
        Max records to return, 1-500. Default 30.
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
            "proprietary_name": proprietary_name,
            "proper_name": proper_name,
            "applicant": applicant,
            "bla_number": bla_number,
            "license_type": license_type,
            "reference_product_proper_name": reference_product_proper_name,
            "reference_product_proprietary_name": reference_product_proprietary_name,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FDAPurpleBook_search_products",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FDAPurpleBook_search_products"]
