"""
PANTHER_ortholog

Find orthologs of a gene across species using PANTHER evolutionary classification. Returns the or...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PANTHER_ortholog(
    gene_id: str,
    organism: Optional[int | Any] = None,
    target_organism: Optional[int | Any] = None,
    ortholog_type: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Find orthologs of a gene across species using PANTHER evolutionary classification. Returns the or...

    Parameters
    ----------
    gene_id : str
        Gene identifier - UniProt accession, Ensembl ID, or gene symbol. Examples: 'P...
    organism : int | Any
        Source organism NCBI taxonomy ID. Default: 9606 (human).
    target_organism : int | Any
        Target organism NCBI taxonomy ID. Default: 10090 (mouse). Others: 10116 (rat)...
    ortholog_type : str | Any
        Ortholog type filter. Options: 'LDO' (least diverged ortholog, default), 'O' ...
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
            "gene_id": gene_id,
            "organism": organism,
            "target_organism": target_organism,
            "ortholog_type": ortholog_type,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PANTHER_ortholog",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PANTHER_ortholog"]
