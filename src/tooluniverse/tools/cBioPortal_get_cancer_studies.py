"""
cBioPortal_get_cancer_studies

Get one page of the cBioPortal study catalogue
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def cBioPortal_get_cancer_studies(
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get one page of the cBioPortal study catalogue. The response reports
    `total_available` (full catalogue size) alongside `count` (studies
    returned) and sets `truncated` when studies were left behind.

    Parameters
    ----------
    limit : int
        Number of studies to return in this page
    offset : int
        0-based index of the first study to return
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
        k: v for k, v in {"limit": limit, "offset": offset}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "cBioPortal_get_cancer_studies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["cBioPortal_get_cancer_studies"]
