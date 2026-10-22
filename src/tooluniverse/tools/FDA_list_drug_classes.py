"""
FDA_list_drug_classes

List FDA Established Pharmacologic Classes and label counts. The ranked class catalog is recovera...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FDA_list_drug_classes(
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List FDA Established Pharmacologic Classes and label counts. The ranked class catalog is recovera...

    Parameters
    ----------
    limit : int
        Maximum number of drug classes to return (default: 20, max: 100)
    offset : int
        Zero-based ranked-class offset. Continue with metadata.next_offset.
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
        k: v for k, v in {"limit": limit, "offset": offset}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FDA_list_drug_classes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FDA_list_drug_classes"]
