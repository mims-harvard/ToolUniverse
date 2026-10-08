"""
DbGaP_get_study

Retrieve one dbGaP study's full public metadata by its phs accession: description, medical condit...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DbGaP_get_study(
    phs_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve one dbGaP study's full public metadata by its phs accession: description, medical condit...

    Parameters
    ----------
    phs_id : str
        dbGaP study accession, e.g. 'phs000681'.
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
    _args = {k: v for k, v in {"phs_id": phs_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "DbGaP_get_study",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DbGaP_get_study"]
