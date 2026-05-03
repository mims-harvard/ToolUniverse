"""
FDAGSRS_get_structure

Get chemical structure data for an FDA-regulated substance by UNII code. Returns SMILES, molecula...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FDAGSRS_get_structure(
    unii: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get chemical structure data for an FDA-regulated substance by UNII code. Returns SMILES, molecula...

    Parameters
    ----------
    unii : str
        FDA UNII code for the chemical substance. Examples: 'R16CO5Y76E' (aspirin), '...
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
    _args = {k: v for k, v in {"unii": unii}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "FDAGSRS_get_structure",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FDAGSRS_get_structure"]
