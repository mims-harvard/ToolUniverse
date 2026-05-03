"""
gwas_get_associations_for_snp

Get all associations for a specific SNP with optional sorting.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def gwas_get_associations_for_snp(
    rs_id: str,
    sort: Optional[str] = None,
    direction: Optional[str] = None,
    size: Optional[int] = None,
    page: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get all associations for a specific SNP with optional sorting.

    Parameters
    ----------
    rs_id : str
        dbSNP rs identifier
    sort : str
        Sort field (e.g., 'p_value', 'or_value')
    direction : str
        Sort direction ('asc' or 'desc')
    size : int
        Number of results to return per page
    page : int
        Page number for pagination
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
            "rs_id": rs_id,
            "sort": sort,
            "direction": direction,
            "size": size,
            "page": page,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "gwas_get_associations_for_snp",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["gwas_get_associations_for_snp"]
