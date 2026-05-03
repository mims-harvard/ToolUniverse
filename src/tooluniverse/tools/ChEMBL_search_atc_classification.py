"""
ChEMBL_search_atc_classification

Search ATC (Anatomical Therapeutic Chemical) classifications for drugs. To find a drug ID, use Ch...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChEMBL_search_atc_classification(
    level4: Optional[str] = None,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search ATC (Anatomical Therapeutic Chemical) classifications for drugs. To find a drug ID, use Ch...

    Parameters
    ----------
    level4 : str
        Filter by ATC level 4 code
    limit : int

    offset : int

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
        for k, v in {"level4": level4, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChEMBL_search_atc_classification",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChEMBL_search_atc_classification"]
