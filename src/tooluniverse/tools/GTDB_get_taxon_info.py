"""
GTDB_get_taxon_info

Get information about a GTDB taxon including its rank, total genome count, higher-rank lineage, a...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GTDB_get_taxon_info(
    operation: str,
    taxon: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get information about a GTDB taxon including its rank, total genome count, higher-rank lineage, a...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_taxon_info)
    taxon : str
        GTDB taxon name with rank prefix (e.g., 'f__Lachnospiraceae', 'd__Bacteria', ...
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
    _args = {k: v for k, v in {
        "operation": operation,
                "taxon": taxon
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "GTDB_get_taxon_info",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["GTDB_get_taxon_info"]
