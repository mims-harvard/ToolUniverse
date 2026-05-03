"""
ModelDB_get_celltype

Get details about a specific neuron/cell type from ModelDB by its cell type ID. Returns the cell ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ModelDB_get_celltype(
    celltype_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get details about a specific neuron/cell type from ModelDB by its cell type ID. Returns the cell ...

    Parameters
    ----------
    celltype_id : str
        Cell type ID from ModelDB. Examples: '259' (Hippocampus CA3 pyramidal GLU cel...
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
    _args = {k: v for k, v in {"celltype_id": celltype_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ModelDB_get_celltype",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ModelDB_get_celltype"]
