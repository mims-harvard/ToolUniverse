"""
LipidMaps_search_by_formula

Search lipids by molecular formula in LIPID MAPS Structure Database. Returns all lipids matching ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LipidMaps_search_by_formula(
    input_value: str,
    output_item: Optional[str] = "all",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search lipids by molecular formula in LIPID MAPS Structure Database. Returns all lipids matching ...

    Parameters
    ----------
    input_value : str
        Molecular formula (e.g., 'C22H32O2', 'C16H32O2'). Standard chemical formula f...
    output_item : str
        Type of output. Options: 'all', 'name', 'smiles', 'classification'.
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

    return get_shared_client().run_one_function(
        {
            "name": "LipidMaps_search_by_formula",
            "arguments": {"input_value": input_value, "output_item": output_item},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LipidMaps_search_by_formula"]
