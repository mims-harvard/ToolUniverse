"""
cBioPortal_get_gene_panel_genes

Get all genes in a specific gene panel. Essential for understanding what genes are covered when a...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def cBioPortal_get_gene_panel_genes(
    gene_panel_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get all genes in a specific gene panel. Essential for understanding what genes are covered when a...

    Parameters
    ----------
    gene_panel_id : str
        Gene panel ID (e.g., 'IMPACT468')
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
    _args = {k: v for k, v in {"gene_panel_id": gene_panel_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "cBioPortal_get_gene_panel_genes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["cBioPortal_get_gene_panel_genes"]
