"""
GDC_get_survival

Get Kaplan-Meier survival data for a GDC/TCGA cancer cohort.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GDC_get_survival(
    project_id: str = "",
    gene_symbol: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get Kaplan-Meier survival data for a GDC/TCGA cancer cohort.

    Parameters
    ----------
    project_id : str
        GDC project identifier (e.g., 'TCGA-BRCA').
    gene_symbol : str, optional
        Gene symbol to filter cases with mutations in this gene.

    Returns
    -------
    dict[str, Any]
    """
    _args = {
        k: v
        for k, v in {
            "project_id": project_id,
            "gene_symbol": gene_symbol,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {"name": "GDC_get_survival", "arguments": _args},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GDC_get_survival"]
