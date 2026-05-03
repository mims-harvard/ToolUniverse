"""
OMIM_get_entry

Get detailed OMIM entry by MIM number. Returns comprehensive information including text descripti...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OMIM_get_entry(
    mim_number: str,
    operation: Optional[str] = None,
    include: Optional[str] = "text,clinicalSynopsis,geneMap",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed OMIM entry by MIM number. Returns comprehensive information including text descripti...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_entry)
    mim_number : str
        OMIM MIM number (e.g., 164730, 219700). Can include OMIM: prefix.
    include : str
        Data sections to include (default: text,clinicalSynopsis,geneMap)
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
            "mim_number": mim_number,
            "include": include,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OMIM_get_entry",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OMIM_get_entry"]
