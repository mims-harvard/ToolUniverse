"""
GWASSumStats_list_studies

List GWAS studies that have deposited full summary statistics with the EBI GWAS Catalog. Unlike t...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GWASSumStats_list_studies(
    size: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    List GWAS studies that have deposited full summary statistics with the EBI GWAS Catalog. Unlike t...

    Parameters
    ----------
    size : int | Any
        Number of studies to return (default 20, max 100).
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
    _args = {k: v for k, v in {"size": size}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "GWASSumStats_list_studies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GWASSumStats_list_studies"]
