"""
MetabolomicsWorkbench_search_compound_by_name

Search for a metabolite/compound by its name using RefMet nomenclature. Returns standardized comp...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MetabolomicsWorkbench_search_compound_by_name(
    input_value: Optional[str] = None,
    compound_name: Optional[str] = None,
    output_item: Optional[str] = "all",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search for a metabolite/compound by its name using RefMet nomenclature. Returns standardized comp...

    Parameters
    ----------
    input_value : str
        Compound/metabolite name to search (e.g., 'Glucose', 'Cholesterol', 'Palmitic...
    compound_name : str
        Alias for input_value.
    output_item : str
        Type of output to return.
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
    _args = {
        k: v
        for k, v in {
            "input_value": input_value,
            "compound_name": compound_name,
            "output_item": output_item,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MetabolomicsWorkbench_search_compound_by_name",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MetabolomicsWorkbench_search_compound_by_name"]
