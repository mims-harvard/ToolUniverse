"""
Harmonizome_get_gene_set_members

Retrieve Harmonizome gene-set members or per-gene associations. Both modes are recoverably pagina...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Harmonizome_get_gene_set_members(
    mode: Optional[str] = "gene_set",
    attribute: Optional[str] = None,
    dataset: Optional[str] = None,
    gene_symbol: Optional[str] = None,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve Harmonizome gene-set members or per-gene associations. Both modes are recoverably pagina...

    Parameters
    ----------
    mode : str
        'gene_set' for member genes of an attribute set (requires attribute + dataset...
    attribute : str
        Attribute/gene-set name for mode='gene_set' (e.g. 'heart', 'liver', a cell ty...
    dataset : str
        Dataset name for mode='gene_set' (e.g. 'GTEx Tissue Gene Expression Profiles'...
    gene_symbol : str
        Gene symbol for mode='gene' (e.g. 'DTD2', 'TP53').
    limit : int
        Maximum number of association rows to return (default 100). Sets can have tho...
    offset : int
        Zero-based association offset. Continue with metadata.next_offset.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Any
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "mode": mode,
            "attribute": attribute,
            "dataset": dataset,
            "gene_symbol": gene_symbol,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Harmonizome_get_gene_set_members",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Harmonizome_get_gene_set_members"]
