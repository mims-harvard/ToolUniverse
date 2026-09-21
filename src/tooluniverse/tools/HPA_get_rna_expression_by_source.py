"""
HPA_get_rna_expression_by_source

Get RNA expression for a gene in a specific biological source, read from HPA's dedicated per-sour...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HPA_get_rna_expression_by_source(
    gene_name: str,
    source_type: str,
    source_name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get RNA expression for a gene in a specific biological source, read from HPA's dedicated per-sour...

    Parameters
    ----------
    gene_name : str
        Gene name or gene symbol, e.g., 'GFAP', 'TP53', 'BRCA1', etc.
    source_type : str
        The type of biological source. Choose from: 'tissue' (51 consensus tissues, n...
    source_name : str
        The specific source name, e.g. 'liver', 'heart_muscle', 'skin', 't_cell', 'he...
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
            "source_type": source_type,
            "source_name": source_name,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HPA_get_rna_expression_by_source",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HPA_get_rna_expression_by_source"]
