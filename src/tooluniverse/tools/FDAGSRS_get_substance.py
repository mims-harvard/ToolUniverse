"""
FDAGSRS_get_substance

Get full FDA substance record by UNII (Unique Ingredient Identifier) code.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FDAGSRS_get_substance(
    unii: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get full FDA substance record by UNII code.

    Parameters
    ----------
    unii : str
        FDA UNII (Unique Ingredient Identifier) code (e.g., 'R16CO5Y76E' for aspirin).
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
            "name": "FDAGSRS_get_substance",
            "arguments": {"unii": unii},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FDAGSRS_get_substance"]
