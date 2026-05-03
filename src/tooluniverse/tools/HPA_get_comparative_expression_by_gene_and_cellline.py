"""
HPA_get_comparative_expression_by_gene_and_cellline

Compare the expression level differences of a gene between a specific cell line and healthy tissu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HPA_get_comparative_expression_by_gene_and_cellline(
    gene_name: str,
    cell_line: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Compare the expression level differences of a gene between a specific cell line and healthy tissu...

    Parameters
    ----------
    gene_name : str
        Gene name or gene symbol, e.g., 'TP53', 'BRCA1', 'EGFR', etc.
    cell_line : str
        Cell line name, supported cell lines include: ishikawa, hela, mcf7, a549, hep...
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
        for k, v in {"gene_name": gene_name, "cell_line": cell_line}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HPA_get_comparative_expression_by_gene_and_cellline",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HPA_get_comparative_expression_by_gene_and_cellline"]
