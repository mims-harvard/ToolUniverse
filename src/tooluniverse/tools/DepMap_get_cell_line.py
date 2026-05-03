"""
DepMap_get_cell_line

Get detailed metadata for a specific cancer cell line. Returns tissue, cancer type, MSI status, p...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DepMap_get_cell_line(
    model_id: Optional[str] = None,
    model_name: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed metadata for a specific cancer cell line. Returns tissue, cancer type, MSI status, p...

    Parameters
    ----------
    model_id : str
        Cell Model Passport ID (e.g., 'SIDM00001')
    model_name : str
        Cell line name (e.g., 'A549', 'MCF7', 'HeLa')
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
        for k, v in {"model_id": model_id, "model_name": model_name}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DepMap_get_cell_line",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DepMap_get_cell_line"]
