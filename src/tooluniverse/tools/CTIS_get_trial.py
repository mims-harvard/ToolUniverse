"""
CTIS_get_trial

Retrieve a single EU CTIS clinical trial by its CT number (format like '2022-503001-38-01'). Retu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CTIS_get_trial(
    ct_number: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve a single EU CTIS clinical trial by its CT number (format like '2022-503001-38-01'). Retu...

    Parameters
    ----------
    ct_number : str
        CTIS CT number, e.g. '2022-503001-38-01'.
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
    _args = {k: v for k, v in {"ct_number": ct_number}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "CTIS_get_trial",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CTIS_get_trial"]
