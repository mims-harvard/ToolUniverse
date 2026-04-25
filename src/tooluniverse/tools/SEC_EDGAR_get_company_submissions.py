"""
SEC_EDGAR_get_company_submissions

Get company profile and recent filing history from SEC EDGAR by CIK number. Returns company name,...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SEC_EDGAR_get_company_submissions(
    cik: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get company profile and recent filing history from SEC EDGAR by CIK number. Returns company name,...

    Parameters
    ----------
    cik : str
        SEC Central Index Key, 10-digit zero-padded string (e.g., '0001682852' for Mo...
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
        "cik": cik
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "SEC_EDGAR_get_company_submissions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["SEC_EDGAR_get_company_submissions"]
