"""
dbsnp_get_variant_by_rsid

Get variant information from dbSNP by rsID. Returns genomic coordinates, alleles, and basic varia...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def dbsnp_get_variant_by_rsid(
    rsid: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get variant information from dbSNP by rsID. Returns genomic coordinates, alleles, and basic varia...

    Parameters
    ----------
    rsid : str
        dbSNP rsID (e.g., 'rs12345', '12345')
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
    _args = {k: v for k, v in {"rsid": rsid}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "dbsnp_get_variant_by_rsid",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["dbsnp_get_variant_by_rsid"]
