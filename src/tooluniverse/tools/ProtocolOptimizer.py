"""
ProtocolOptimizer

Reviews an initial protocol and delivers targeted revisions that improve clarity, feasibility, ri...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ProtocolOptimizer(
    initial_protocol: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Reviews an initial protocol and delivers targeted revisions that improve clarity, feasibility, ri...

    Parameters
    ----------
    initial_protocol : str

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

    return get_shared_client().run_one_function(
        {
            "name": "ProtocolOptimizer",
            "arguments": {"initial_protocol": initial_protocol},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ProtocolOptimizer"]
