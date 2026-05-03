"""
HPA_get_subcellular_location

Get annotated subcellular locations for a protein using optimized columns parameter. Retrieves bo...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HPA_get_subcellular_location(
    gene_name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get annotated subcellular locations for a protein using optimized columns parameter. Retrieves bo...

    Parameters
    ----------
    gene_name : str
        Gene name or gene symbol, e.g., 'CCNB1', 'TP53', 'EGFR', etc.
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
    _args = {k: v for k, v in {"gene_name": gene_name}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "HPA_get_subcellular_location",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HPA_get_subcellular_location"]
