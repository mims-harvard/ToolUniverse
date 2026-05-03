"""
GDC_get_survival

Get Kaplan-Meier survival data for a GDC/TCGA cancer cohort. Returns time-to-event data with cens...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GDC_get_survival(
    project_id: str,
    gene_symbol: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get Kaplan-Meier survival data for a GDC/TCGA cancer cohort. Returns time-to-event data with cens...

    Parameters
    ----------
    project_id : str
        GDC project identifier (e.g., 'TCGA-BRCA', 'TCGA-LUAD', 'TCGA-GBM')
    gene_symbol : str
        Optional: gene symbol to filter cases with mutations in this gene (e.g., 'TP5...
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
        for k, v in {"project_id": project_id, "gene_symbol": gene_symbol}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GDC_get_survival",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GDC_get_survival"]
