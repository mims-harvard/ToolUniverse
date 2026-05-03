"""
LipidMaps_search_by_name

Search for lipids by exact abbreviation in LIPID MAPS Structure Database. IMPORTANT: Only exact l...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LipidMaps_search_by_name(
    input_value: str,
    output_item: Optional[str] = "all",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for lipids by exact abbreviation in LIPID MAPS Structure Database. IMPORTANT: Only exact l...

    Parameters
    ----------
    input_value : str
        Exact lipid abbreviation used in lipidomics (e.g., 'DHA', 'EPA', 'PC 16:0/18:...
    output_item : str
        Type of output. Options: 'all', 'name', 'formula', 'exactmass', 'smiles', 'cl...
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
    _args = {
        k: v
        for k, v in {"input_value": input_value, "output_item": output_item}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "LipidMaps_search_by_name",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LipidMaps_search_by_name"]
