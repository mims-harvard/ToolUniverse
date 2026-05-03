"""
OpenFDA_search_drug_approvals

Search the FDA Drugs@FDA database for drug approval records by drug name, sponsor/manufacturer, o...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenFDA_search_drug_approvals(
    operation: str,
    drug_name: Optional[str | Any] = None,
    sponsor: Optional[str | Any] = None,
    application_number: Optional[str | Any] = None,
    limit: Optional[int] = 5,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search the FDA Drugs@FDA database for drug approval records by drug name, sponsor/manufacturer, o...

    Parameters
    ----------
    operation : str
        Operation type
    drug_name : str | Any
        Drug name to search (brand or generic, e.g., 'aspirin', 'metformin', 'Lipitor...
    sponsor : str | Any
        Sponsor/manufacturer name (e.g., 'PFIZER', 'MERCK', 'NOVARTIS')
    application_number : str | Any
        FDA application number (e.g., 'NDA021457', 'ANDA078372', 'BLA125554')
    limit : int
        Maximum number of results (default: 5, max: 20)
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
            "operation": operation,
            "drug_name": drug_name,
            "sponsor": sponsor,
            "application_number": application_number,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenFDA_search_drug_approvals",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenFDA_search_drug_approvals"]
