"""
HPA_get_biological_processes_by_gene

Get biological process information for a gene, with special focus on key processes like apoptosis...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HPA_get_biological_processes_by_gene(
    gene_name: str,
    filter_processes: bool,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get biological process information for a gene, with special focus on key processes like apoptosis...

    Parameters
    ----------
    gene_name : str
        Gene name or gene symbol, e.g., 'TP53', 'CDK1', 'CASP3', etc.
    filter_processes : bool
        Whether to filter and focus on specific biological processes (apoptosis, cell...
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
        for k, v in {
            "gene_name": gene_name,
            "filter_processes": filter_processes,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HPA_get_biological_processes_by_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HPA_get_biological_processes_by_gene"]
