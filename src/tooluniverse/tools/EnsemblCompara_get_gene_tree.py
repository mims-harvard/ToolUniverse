"""
EnsemblCompara_get_gene_tree

Get an Ensembl Compara phylogenetic gene tree and its complete member count. Members are recovera...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EnsemblCompara_get_gene_tree(
    gene: str,
    species: Optional[str] = None,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get an Ensembl Compara phylogenetic gene tree and its complete member count. Members are recovera...

    Parameters
    ----------
    gene : str
        Gene symbol or Ensembl gene ID. Examples: 'TP53', 'BRCA1', 'ENSG00000141510'....
    species : str
        Species (default: 'human'). Used when providing a gene symbol. Examples: 'hum...
    limit : int
        Maximum tree members per page (default 50).
    offset : int
        Zero-based member offset. Continue with data.next_offset.
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
            "species": species,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EnsemblCompara_get_gene_tree",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EnsemblCompara_get_gene_tree"]
