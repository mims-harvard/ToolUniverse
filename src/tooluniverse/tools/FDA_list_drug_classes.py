"""
FDA_list_drug_classes

List FDA pharmacological drug classes (Established Pharmacologic Class, EPC) and the number of dr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FDA_list_drug_classes(
    limit: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List FDA pharmacological drug classes (Established Pharmacologic Class, EPC) and the number of dr...

    Parameters
    ----------
    limit : int
        Maximum number of drug classes to return (default: 20, max: 100)
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
        {"name": "FDA_list_drug_classes", "arguments": {"limit": limit}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FDA_list_drug_classes"]
