"""
BAR_get_gene_info

Get plant gene annotation from the BAR (Bio-Analytic Resource for Plant Biology, a Global Core Bi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BAR_get_gene_info(
    gene_id: str,
    species: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get plant gene annotation from the BAR (Bio-Analytic Resource for Plant Biology, a Global Core Bi...

    Parameters
    ----------
    gene_id : str
        Gene locus identifier, e.g. 'AT1G01010' (Arabidopsis).
    species : str
        Species, e.g. 'arabidopsis' (default).
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
        for k, v in {"gene_id": gene_id, "species": species}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BAR_get_gene_info",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BAR_get_gene_info"]
