"""
RegulomeDB_query_variant

Query RegulomeDB for regulatory variant annotations using rsID
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RegulomeDB_query_variant(
    rsid: Optional[str] = None,
    variant: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Query RegulomeDB for regulatory variant annotations using rsID

    Parameters
    ----------
    rsid : str
        dbSNP rsID (e.g., 'rs4994', 'rs429358')
    variant : str
        Alias for rsid. dbSNP rsID (e.g., 'rs7903146', 'rs429358').
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
        k: v for k, v in {"rsid": rsid, "variant": variant}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RegulomeDB_query_variant",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RegulomeDB_query_variant"]
