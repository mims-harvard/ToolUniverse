"""
MSigDB_get_gene_set_members

Get all gene members of an MSigDB gene set by exact name. Returns parsed gene list (unlike MSigDB...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MSigDB_get_gene_set_members(
    gene_set_name: str,
    operation: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get all gene members of an MSigDB gene set by exact name. Returns parsed gene list (unlike MSigDB...

    Parameters
    ----------
    operation : str

    gene_set_name : str
        Exact MSigDB gene set name (e.g., 'ZNF549_TARGET_GENES', 'MIR675_3P_TARGET_GE...
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
        for k, v in {"operation": operation, "gene_set_name": gene_set_name}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MSigDB_get_gene_set_members",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MSigDB_get_gene_set_members"]
