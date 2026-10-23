"""
EnsemblPheno_get_by_gene

Get phenotype associations for a gene from Ensembl with limit/offset pagination and explicit tota...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EnsemblPheno_get_by_gene(
    gene: str,
    species: Optional[str] = "homo_sapiens",
    limit: Optional[int] = 200,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get phenotype associations for a gene from Ensembl with limit/offset pagination and explicit tota...

    Parameters
    ----------
    species : str
        Species name. Use 'homo_sapiens' for human. Default: 'homo_sapiens'.
    gene : str
        Gene symbol. Examples: 'BRCA1', 'TP53', 'EGFR', 'KRAS', 'BRAF'.
    limit : int
        Maximum number of deduplicated phenotype associations to return in this page.
    offset : int
        Zero-based association offset. Use data.next_offset for the next page.
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
            "species": species,
            "gene": gene,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EnsemblPheno_get_by_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EnsemblPheno_get_by_gene"]
