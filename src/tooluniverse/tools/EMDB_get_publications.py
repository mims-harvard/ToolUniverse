"""
EMDB_get_publications

Get publication information for an EMDB entry including journal articles, preprints, and citation...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EMDB_get_publications(
    emdb_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get publication information for an EMDB entry including journal articles, preprints, and citation...

    Parameters
    ----------
    emdb_id : str
        EMDB structure identifier in format 'EMD-####' (e.g., 'EMD-1234', 'EMD-0001')...
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
    _args = {k: v for k, v in {"emdb_id": emdb_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "EMDB_get_publications",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EMDB_get_publications"]
