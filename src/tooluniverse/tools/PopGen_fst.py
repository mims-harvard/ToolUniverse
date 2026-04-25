"""
PopGen_fst

Calculate simplified Weir-Cockerham Fst between two populations given allele frequencies and samp...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PopGen_fst(
    operation: str,
    p1: float,
    p2: float,
    n1: int,
    n2: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Calculate simplified Weir-Cockerham Fst between two populations given allele frequencies and samp...

    Parameters
    ----------
    operation : str
        Operation type
    p1 : float
        Allele frequency in population 1 [0, 1]
    p2 : float
        Allele frequency in population 2 [0, 1]
    n1 : int
        Sample size (number of individuals) for population 1
    n2 : int
        Sample size (number of individuals) for population 2
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
            "p1": p1,
            "p2": p2,
            "n1": n1,
            "n2": n2,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PopGen_fst",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PopGen_fst"]
