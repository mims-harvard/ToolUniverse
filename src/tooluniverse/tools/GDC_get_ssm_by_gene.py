"""
GDC_get_ssm_by_gene

Get somatic mutations (SSMs) for a gene across TCGA/GDC projects. Returns mutation type, genomic ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GDC_get_ssm_by_gene(
    gene_symbol: str,
    project_id: Optional[str] = None,
    size: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get somatic mutations (SSMs) for a gene across TCGA/GDC projects. Returns mutation type, genomic ...

    Parameters
    ----------
    gene_symbol : str
        Gene symbol (e.g., 'TP53', 'EGFR', 'BRAF', 'KRAS')
    project_id : str
        Optional: Filter by project (e.g., 'TCGA-BRCA', 'TCGA-LUAD')
    size : int
        Number of results (1–100)
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
            "gene_symbol": gene_symbol,
            "project_id": project_id,
            "size": size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GDC_get_ssm_by_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GDC_get_ssm_by_gene"]
