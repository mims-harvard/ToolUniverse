"""
PGSCatalog_get_score

Retrieve the full metadata for a specific polygenic score from the PGS Catalog by its PGS id (e.g...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PGSCatalog_get_score(
    pgs_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve the full metadata for a specific polygenic score from the PGS Catalog by its PGS id (e.g...

    Parameters
    ----------
    pgs_id : str
        PGS Catalog score id, e.g. 'PGS000001'.
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
    _args = {k: v for k, v in {"pgs_id": pgs_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PGSCatalog_get_score",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PGSCatalog_get_score"]
