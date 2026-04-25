"""
Sequence_gc_content

Calculate GC content of a DNA or RNA sequence. Reports GC count, GC fraction, GC percentage, and ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Sequence_gc_content(
    operation: str,
    sequence: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Calculate GC content of a DNA or RNA sequence. Reports GC count, GC fraction, GC percentage, and ...

    Parameters
    ----------
    operation : str
        Operation type
    sequence : str
        DNA or RNA sequence string
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
        k: v
        for k, v in {"operation": operation, "sequence": sequence}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Sequence_gc_content",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Sequence_gc_content"]
