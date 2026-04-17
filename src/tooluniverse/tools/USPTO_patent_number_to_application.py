"""
USPTO_patent_number_to_application

Convert any patent number format to a USPTO application number. Accepts grant numbers (US9629826B...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def USPTO_patent_number_to_application(
    patent_number: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Convert any patent number format to a USPTO application number. Accepts grant numbers (US9629826B...

    Parameters
    ----------
    patent_number : str
        Patent number in any format: grant (US9629826B2), application (14/966,067), o...
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
        "patent_number": patent_number
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "USPTO_patent_number_to_application",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["USPTO_patent_number_to_application"]
