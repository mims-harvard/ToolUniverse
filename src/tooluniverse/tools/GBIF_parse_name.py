"""
GBIF_parse_name

Parse one or more scientific name strings into structured components using the GBIF name parser. ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GBIF_parse_name(
    name: Optional[str] = None,
    names: Optional[list[str]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Parse one or more scientific name strings into structured components using the GBIF name parser. ...

    Parameters
    ----------
    name : str
        A single scientific name string to parse, e.g. 'Panthera leo (Linnaeus, 1758)...
    names : list[str]
        A list of scientific name strings to parse in one call, e.g. ['Homo sapiens L...
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
    _args = {k: v for k, v in {"name": name, "names": names}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "GBIF_parse_name",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GBIF_parse_name"]
