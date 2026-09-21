"""
GIAB_list_directory

Browse NIST Genome in a Bottle's (GIAB) benchmark file release tree -- the reference-standard hig...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GIAB_list_directory(
    path: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Browse NIST Genome in a Bottle's (GIAB) benchmark file release tree -- the reference-standard hig...

    Parameters
    ----------
    path : str
        Path relative to the GIAB release root, e.g. '' (top level), 'AshkenazimTrio'...
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
    _args = {k: v for k, v in {"path": path}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "GIAB_list_directory",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GIAB_list_directory"]
