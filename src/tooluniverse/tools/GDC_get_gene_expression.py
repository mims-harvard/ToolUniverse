"""
GDC_get_gene_expression

Query RNA-Seq gene expression files from GDC/TCGA projects. Returns file metadata for expression ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GDC_get_gene_expression(
    project_id: str,
    gene_id: Optional[str] = None,
    size: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Query RNA-Seq gene expression files from GDC/TCGA projects. Returns file metadata for expression ...

    Parameters
    ----------
    project_id : str
        GDC project (e.g., 'TCGA-BRCA', 'TCGA-LUAD', 'TCGA-GBM')
    gene_id : str
        Optional: Ensembl gene ID (e.g., 'ENSG00000141510' for TP53)
    size : int
        Number of results
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
        for k, v in {"project_id": project_id, "gene_id": gene_id, "size": size}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GDC_get_gene_expression",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GDC_get_gene_expression"]
