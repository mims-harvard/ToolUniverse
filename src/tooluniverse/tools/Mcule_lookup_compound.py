"""
Mcule_lookup_compound

Look up purchasable compounds on Mcule by SMILES, InChIKey, or Mcule ID. Mcule aggregates 30M+ co...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Mcule_lookup_compound(
    operation: str,
    query: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Look up purchasable compounds on Mcule by SMILES, InChIKey, or Mcule ID. Mcule aggregates 30M+ co...

    Parameters
    ----------
    operation : str
        Operation type
    query : str
        Chemical identifier to look up: SMILES string, InChIKey, or Mcule ID (e.g., C...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    return get_shared_client().run_one_function(
        {
            "name": "Mcule_lookup_compound",
            "arguments": {"operation": operation, "query": query},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Mcule_lookup_compound"]
