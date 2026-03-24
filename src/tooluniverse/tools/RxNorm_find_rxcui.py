"""
RxNorm_find_rxcui

Resolve a drug name to its RxNorm RXCUI (RxNorm Concept Unique Identifier) using the NLM RxNorm A...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RxNorm_find_rxcui(
    drug_name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Resolve a drug name to its RxNorm RXCUI (RxNorm Concept Unique Identifier) using the NLM RxNorm A...

    Parameters
    ----------
    drug_name : str
        Drug name to look up (generic, brand, or synonym). Examples: 'metformin', 'Li...
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
    _args = {k: v for k, v in {"drug_name": drug_name}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "RxNorm_find_rxcui",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RxNorm_find_rxcui"]
