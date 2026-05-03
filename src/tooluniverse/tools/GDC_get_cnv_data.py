"""
GDC_get_cnv_data

Query copy number variation (CNV) files from GDC/TCGA projects. Returns CNV segment and gene-leve...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GDC_get_cnv_data(
    project_id: str,
    gene_symbol: Optional[str] = None,
    size: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Query copy number variation (CNV) files from GDC/TCGA projects. Returns CNV segment and gene-leve...

    Parameters
    ----------
    project_id : str
        GDC project (e.g., 'TCGA-BRCA')
    gene_symbol : str
        Optional: Gene symbol to focus analysis
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
        for k, v in {
            "project_id": project_id,
            "gene_symbol": gene_symbol,
            "size": size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GDC_get_cnv_data",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GDC_get_cnv_data"]
