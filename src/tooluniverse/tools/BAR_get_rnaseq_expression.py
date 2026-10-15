"""
BAR_get_rnaseq_expression

Get RNA-seq gene expression data from the BAR (Bio-Analytic Resource for Plant Biology). database...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BAR_get_rnaseq_expression(
    gene_id: str,
    species: Optional[str] = None,
    database: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get RNA-seq gene expression data from the BAR (Bio-Analytic Resource for Plant Biology). database...

    Parameters
    ----------
    gene_id : str
        Gene locus identifier, e.g. 'At1g01010' (Arabidopsis).
    species : str
        Species, e.g. 'arabidopsis' (default).
    database : str
        RNA-seq dataset, e.g. 'single_cell' (default).
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
            "gene_id": gene_id,
            "species": species,
            "database": database,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BAR_get_rnaseq_expression",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BAR_get_rnaseq_expression"]
