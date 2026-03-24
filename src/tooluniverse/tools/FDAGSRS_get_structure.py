"""
FDAGSRS_get_structure

Get chemical structure data (SMILES, formula, InChIKey) for an FDA substance by UNII code.
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
    Get chemical structure data for an FDA substance by UNII code.

    Parameters
    ----------
    unii : str
        FDA UNII code (e.g., 'R16CO5Y76E' for aspirin, '9100L32L2N' for ibuprofen).
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
    return get_shared_client().run_one_function(
        {
            "name": "FDAGSRS_get_structure",
            "arguments": {"unii": unii},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FDAGSRS_get_structure"]
