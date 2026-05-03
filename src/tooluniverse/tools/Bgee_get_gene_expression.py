"""
Bgee_get_gene_expression

Get expression data for a gene across tissues and organs from the Bgee database. Returns where a ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Bgee_get_gene_expression(
    gene_id: str,
    species_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get expression data for a gene across tissues and organs from the Bgee database. Returns where a ...

    Parameters
    ----------
    gene_id : str
        Ensembl gene ID. Examples: 'ENSG00000141510' (human TP53), 'ENSMUSG0000005955...
    species_id : str
        NCBI taxonomy ID for the species. Examples: '9606' (human), '10090' (mouse), ...
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
        for k, v in {"gene_id": gene_id, "species_id": species_id}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Bgee_get_gene_expression",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Bgee_get_gene_expression"]
