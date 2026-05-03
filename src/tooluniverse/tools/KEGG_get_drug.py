"""
KEGG_get_drug

Get detailed KEGG drug information including names, formula, molecular weight, drug targets, asso...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def KEGG_get_drug(
    drug_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed KEGG drug information including names, formula, molecular weight, drug targets, asso...

    Parameters
    ----------
    drug_id : str
        KEGG drug ID in D##### format (e.g., 'D00109' for aspirin, 'D01441' for imati...
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
    _args = {k: v for k, v in {"drug_id": drug_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "KEGG_get_drug",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["KEGG_get_drug"]
