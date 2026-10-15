"""
REBASE_list_isoschizomers

List every restriction enzyme sharing a prototype with the named enzyme, i.e. all enzymes with th...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def REBASE_list_isoschizomers(
    name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List every restriction enzyme sharing a prototype with the named enzyme, i.e. all enzymes with th...

    Parameters
    ----------
    name : str
        Enzyme name to find isoschizomers of, e.g. 'EcoRI'.
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
            "name": "REBASE_list_isoschizomers",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["REBASE_list_isoschizomers"]
