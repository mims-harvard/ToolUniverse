"""
BacDive_get_strain

Retrieve one BacDive strain's curated phenotype: taxonomy down to species, cell morphology and Gr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BacDive_get_strain(
    bacdive_id: int | str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve one BacDive strain's curated phenotype: taxonomy down to species, cell morphology and Gr...

    Parameters
    ----------
    bacdive_id : int | str
        BacDive strain ID, e.g. 24493.
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
    _args = {k: v for k, v in {"bacdive_id": bacdive_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "BacDive_get_strain",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BacDive_get_strain"]
