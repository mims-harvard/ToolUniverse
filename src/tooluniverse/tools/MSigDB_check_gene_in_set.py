"""
MSigDB_check_gene_in_set

Check if a specific gene is a member of an MSigDB gene set. Covers GTRD transcription factor targ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MSigDB_check_gene_in_set(
    gene_set_name: str,
    gene: str,
    operation: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Check if a specific gene is a member of an MSigDB gene set. Covers GTRD transcription factor targ...

    Parameters
    ----------
    operation : str

    gene_set_name : str
        Exact gene set name (e.g., 'ZNF549_TARGET_GENES', 'ESC_V6.5_UP_EARLY.V1_DN', ...
    gene : str
        Gene symbol to check (e.g., 'SELENOP', 'TP53', 'CD37')
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
            "gene_set_name": gene_set_name,
            "gene": gene,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MSigDB_check_gene_in_set",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MSigDB_check_gene_in_set"]
