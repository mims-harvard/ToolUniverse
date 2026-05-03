"""
ZINC_get_compound

Get detailed information for a ZINC compound by its ID, including SMILES structure, molecular pro...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ZINC_get_compound(
    operation: str,
    zinc_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information for a ZINC compound by its ID, including SMILES structure, molecular pro...

    Parameters
    ----------
    operation : str
        Operation type
    zinc_id : str
        ZINC compound identifier, e.g., ZINC000000000053 (aspirin), ZINC000000001084 ...
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
    _args = {
        k: v
        for k, v in {"operation": operation, "zinc_id": zinc_id}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ZINC_get_compound",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ZINC_get_compound"]
