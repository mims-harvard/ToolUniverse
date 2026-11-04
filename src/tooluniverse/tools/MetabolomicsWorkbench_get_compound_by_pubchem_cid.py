"""
MetabolomicsWorkbench_get_compound_by_pubchem_cid

Get metabolite information by PubChem compound ID (CID). Useful for cross-referencing with PubChe...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MetabolomicsWorkbench_get_compound_by_pubchem_cid(
    input_value: str,
    output_item: Optional[str] = "all",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get metabolite information by PubChem compound ID (CID). Useful for cross-referencing with PubChe...

    Parameters
    ----------
    input_value : str
        PubChem compound ID (CID) as a string (e.g., '311' for citric acid).
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
        for k, v in {"input_value": input_value, "output_item": output_item}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MetabolomicsWorkbench_get_compound_by_pubchem_cid",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MetabolomicsWorkbench_get_compound_by_pubchem_cid"]
