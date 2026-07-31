"""
PanglaoDB_list_cell_types

List the cell types catalogued in PanglaoDB (panglaodb.se), each with the organ(s) it appears in ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PanglaoDB_list_cell_types(
    organ: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    List the cell types catalogued in PanglaoDB (panglaodb.se), each with the organ(s) it appears in ...

    Parameters
    ----------
    organ : str
        Optional organ filter, e.g. 'Liver', 'Immune system', 'Brain', 'GI tract'. Ca...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"organ": organ}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PanglaoDB_list_cell_types",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PanglaoDB_list_cell_types"]
