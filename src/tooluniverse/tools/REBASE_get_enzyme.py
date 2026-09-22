"""
REBASE_get_enzyme

Look up a restriction enzyme in REBASE, the reference catalogue of ~6,000 enzymes from New Englan...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def REBASE_get_enzyme(
    name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Look up a restriction enzyme in REBASE, the reference catalogue of ~6,000 enzymes from New Englan...

    Parameters
    ----------
    name : str
        Enzyme name, e.g. 'EcoRI', 'BamHI', 'SmaI'. Matched case-insensitively.
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
    _args = {k: v for k, v in {"name": name}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "REBASE_get_enzyme",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["REBASE_get_enzyme"]
