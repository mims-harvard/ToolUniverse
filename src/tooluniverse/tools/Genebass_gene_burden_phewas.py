"""
Genebass_gene_burden_phewas

Page through all Genebass gene-burden PheWAS associations after stable ascending p-value sorting....
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Genebass_gene_burden_phewas(
    gene: str,
    burden_set: Optional[str] = "pLoF",
    limit: Optional[int] = 25,
    offset: Optional[int] = 0,
    max_pval: Optional[float] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Page through all Genebass gene-burden PheWAS associations after stable ascending p-value sorting....

    Parameters
    ----------
    gene : str
        Ensembl gene ID (e.g. 'ENSG00000148737') or gene symbol (e.g. 'TCF7L2'). Symb...
    burden_set : str
        Variant category aggregated in the burden test. One of: 'pLoF' (default), 'mi...
    limit : int
        Maximum number of phenotype associations to return (sorted by ascending burde...
    offset : int
        Zero-based offset into filtered, p-value-sorted burden associations.
    max_pval : float
        Optional: only return associations with burden p-value <= this threshold (e.g...
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
            "gene": gene,
            "burden_set": burden_set,
            "limit": limit,
            "offset": offset,
            "max_pval": max_pval,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Genebass_gene_burden_phewas",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Genebass_gene_burden_phewas"]
