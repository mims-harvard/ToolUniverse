"""
DepMap_get_gene_dependencies

Get the CRISPR knockout fitness scores of a gene across cancer cell lines and organoids from DepM...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DepMap_get_gene_dependencies(
    gene_symbol: str,
    model_id: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get the CRISPR knockout fitness scores of a gene across cancer cell lines and organoids from DepM...

    Parameters
    ----------
    gene_symbol : str
        Gene symbol (e.g., 'EGFR', 'KRAS', 'TP53')
    model_id : str
        Optional: keep the screens of one model. A model id (e.g. 'SIDM00903') or a m...
    limit : int
        Rows per page (default 50, maximum 500).
    offset : int
        Rows to skip (default 0). Continue with next_offset while has_more is true.
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
            "model_id": model_id,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DepMap_get_gene_dependencies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DepMap_get_gene_dependencies"]
