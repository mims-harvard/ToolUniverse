"""
ARCHS4_get_gene_expression

Get gene expression levels across human or mouse tissues and cell lines from ARCHS4 (All RNA-seq ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ARCHS4_get_gene_expression(
    gene: str,
    species: Optional[str | Any] = "human",
    type_: Optional[str | Any] = "tissue",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get gene expression levels across human or mouse tissues and cell lines from ARCHS4 (All RNA-seq ...

    Parameters
    ----------
    gene : str
        Gene symbol (e.g., TP53, BRCA1, EGFR, MYC)
    species : str | Any
        Species: human or mouse (default: human)
    type_ : str | Any
        Expression type: tissue (organs/tissues) or cellline (cell lines). Default: t...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"gene": gene, "species": species, "type": type_}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ARCHS4_get_gene_expression",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ARCHS4_get_gene_expression"]
