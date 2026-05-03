"""
KEGG_get_compound

Get KEGG compound/metabolite details including names, formula, molecular weight, associated pathw...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def KEGG_get_compound(
    compound_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get KEGG compound/metabolite details including names, formula, molecular weight, associated pathw...

    Parameters
    ----------
    compound_id : str
        KEGG compound ID (e.g., 'C00002' for ATP, 'C00031' for D-Glucose, 'C00033' fo...
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
    _args = {k: v for k, v in {"compound_id": compound_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "KEGG_get_compound",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["KEGG_get_compound"]
