"""
NEB_Tm_list_polymerases

List all NEB DNA polymerase products available for Tm calculation. Returns product codes (prodcod...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NEB_Tm_list_polymerases(
    filter: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    List all NEB DNA polymerase products available for Tm calculation. Returns product codes (prodcod...

    Parameters
    ----------
    filter : str | Any
        Optional keyword to filter products by name, product code, or catalog number....
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {
        "filter": filter
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "NEB_Tm_list_polymerases",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["NEB_Tm_list_polymerases"]
