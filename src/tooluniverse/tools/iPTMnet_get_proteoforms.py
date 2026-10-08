"""
iPTMnet_get_proteoforms

NOTE (checked 2026-10-08): iPTMnet's REST API (research.bioinformatics.udel.edu/iptmnet/api) has ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def iPTMnet_get_proteoforms(
    uniprot_id: str,
    operation: Optional[str] = "get_proteoforms",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    NOTE (checked 2026-10-08): iPTMnet's REST API (research.bioinformatics.udel.edu/iptmnet/api) has ...

    Parameters
    ----------
    operation : str
        Operation type
    uniprot_id : str
        UniProt accession, e.g., P04637 (TP53), P00533 (EGFR), P31749 (AKT1)
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"operation": operation, "uniprot_id": uniprot_id}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "iPTMnet_get_proteoforms",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["iPTMnet_get_proteoforms"]
