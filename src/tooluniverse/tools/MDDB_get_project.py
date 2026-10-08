"""
MDDB_get_project

Retrieve one MDDB molecular dynamics project's simulation parameters: force field, temperature, e...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MDDB_get_project(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve one MDDB molecular dynamics project's simulation parameters: force field, temperature, e...

    Parameters
    ----------
    accession : str
        MDDB project accession, e.g. 'MD-A001UA'.
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
    _args = {k: v for k, v in {"accession": accession}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "MDDB_get_project",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MDDB_get_project"]
