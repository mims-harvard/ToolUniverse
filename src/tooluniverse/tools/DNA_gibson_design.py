"""
DNA_gibson_design

Design Gibson Assembly overlaps for seamless DNA fragment assembly. For each fragment, computes t...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DNA_gibson_design(
    operation: str,
    fragments: list[str],
    overlap_length: Optional[int | Any] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Design Gibson Assembly overlaps for seamless DNA fragment assembly. For each fragment, computes t...

    Parameters
    ----------
    operation : str
        Operation type
    fragments : list[str]
        List of DNA fragment sequences (at least 2). Each must be longer than overlap...
    overlap_length : int | Any
        Overlap length in bp for Gibson Assembly (default: 20 bp). Must be at least 1.
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
    _args = {k: v for k, v in {
        "operation": operation,
                "fragments": fragments,
                "overlap_length": overlap_length
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "DNA_gibson_design",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["DNA_gibson_design"]
