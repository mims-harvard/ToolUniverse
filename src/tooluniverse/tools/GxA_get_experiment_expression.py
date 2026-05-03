"""
GxA_get_experiment_expression

Get gene expression data from a specific Expression Atlas experiment. Returns expression levels a...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GxA_get_experiment_expression(
    experiment_accession: str,
    gene_id: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get gene expression data from a specific Expression Atlas experiment. Returns expression levels a...

    Parameters
    ----------
    experiment_accession : str
        Expression Atlas experiment accession (e.g., 'E-MTAB-2836' for human tissues ...
    gene_id : str
        Optional Ensembl gene ID to filter expression data for a specific gene (e.g.,...
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
            "experiment_accession": experiment_accession,
            "gene_id": gene_id,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GxA_get_experiment_expression",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GxA_get_experiment_expression"]
