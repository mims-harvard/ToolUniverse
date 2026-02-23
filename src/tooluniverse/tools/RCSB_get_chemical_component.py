"""
RCSB_get_chemical_component

Get detailed chemical component information from the RCSB Protein Data Bank by 3-letter component...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RCSB_get_chemical_component(
    comp_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed chemical component information from the RCSB Protein Data Bank by 3-letter component...

    Parameters
    ----------
    comp_id : str
        3-letter chemical component ID in uppercase (e.g., 'ATP', 'HEM', 'NAG', 'STI'...
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

    return get_shared_client().run_one_function(
        {"name": "RCSB_get_chemical_component", "arguments": {"comp_id": comp_id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RCSB_get_chemical_component"]
