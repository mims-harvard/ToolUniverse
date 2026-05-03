"""
PopGen_inbreeding

Compute inbreeding coefficient F for a known pedigree type over one or more generations. Supports...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PopGen_inbreeding(
    operation: str,
    pedigree: str,
    generations: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Compute inbreeding coefficient F for a known pedigree type over one or more generations. Supports...

    Parameters
    ----------
    operation : str
        Operation type
    pedigree : str
        Pedigree type (e.g., 'half-sib', 'first-cousin', 'full-sib')
    generations : int
        Number of successive inbreeding generations (default 1)
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
        for k, v in {
            "operation": operation,
            "pedigree": pedigree,
            "generations": generations,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PopGen_inbreeding",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PopGen_inbreeding"]
