"""
NIHDSLD_get_label

Retrieve one dietary supplement's full label from the NIH DSLD: every ingredient with its per-ser...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NIHDSLD_get_label(
    product_id: str | int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve one dietary supplement's full label from the NIH DSLD: every ingredient with its per-ser...

    Parameters
    ----------
    product_id : str | int
        DSLD product identifier, e.g. 20581.
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
    _args = {k: v for k, v in {"product_id": product_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "NIHDSLD_get_label",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NIHDSLD_get_label"]
