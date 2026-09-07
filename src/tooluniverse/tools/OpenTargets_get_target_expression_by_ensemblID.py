"""
OpenTargets_get_target_expression_by_ensemblID

Retrieve baseline expression summary statistics for a target across tissues and cell types (GTEx,...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenTargets_get_target_expression_by_ensemblID(
    ensemblId: str,
    size: Optional[int] = 250,
    index: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve baseline expression summary statistics for a target across tissues and cell types (GTEx,...

    Parameters
    ----------
    ensemblId : str
        Ensembl gene ID of the target (e.g., 'ENSG00000146648' for EGFR).
    size : int
        Number of expression rows to return per page (default 250, max 3000). Targets...
    index : int
        0-based page index (default 0). Use with `size` to walk the remaining rows wh...
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
        for k, v in {"ensemblId": ensemblId, "size": size, "index": index}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenTargets_get_target_expression_by_ensemblID",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenTargets_get_target_expression_by_ensemblID"]
