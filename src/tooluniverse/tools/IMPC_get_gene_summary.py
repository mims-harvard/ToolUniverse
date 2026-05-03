"""
IMPC_get_gene_summary

Get mouse gene summary from IMPC including phenotyping status, viability, ortholog info, and MP/H...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IMPC_get_gene_summary(
    gene_symbol: Optional[str] = None,
    mgi_id: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get mouse gene summary from IMPC including phenotyping status, viability, ortholog info, and MP/H...

    Parameters
    ----------
    gene_symbol : str
        Mouse gene symbol (e.g., 'Trp53', 'Brca1', 'Wdr7'). Case-sensitive. Use mouse...
    mgi_id : str
        MGI accession ID (e.g., 'MGI:98834'). Use if gene symbol is ambiguous.
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
        for k, v in {"gene_symbol": gene_symbol, "mgi_id": mgi_id}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "IMPC_get_gene_summary",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IMPC_get_gene_summary"]
