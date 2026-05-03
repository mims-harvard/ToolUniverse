"""
UniProtIDMap_gene_to_uniprot

Convert gene names or symbols to UniProt accessions using the UniProt ID Mapping service. Shortcu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniProtIDMap_gene_to_uniprot(
    gene_names: str,
    tax_id: Optional[int] = 9606,
    reviewed_only: Optional[bool | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Convert gene names or symbols to UniProt accessions using the UniProt ID Mapping service. Shortcu...

    Parameters
    ----------
    gene_names : str
        Comma-separated gene symbols. Examples: 'TP53', 'BRCA1,TP53,EGFR,KRAS', 'INS,...
    tax_id : int
        NCBI Taxonomy ID. Required. 9606 = human, 10090 = mouse, 10116 = rat, 7227 = ...
    reviewed_only : bool | Any
        If true, return only Swiss-Prot (reviewed) entries. Default: false (all UniPr...
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
            "gene_names": gene_names,
            "tax_id": tax_id,
            "reviewed_only": reviewed_only,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "UniProtIDMap_gene_to_uniprot",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UniProtIDMap_gene_to_uniprot"]
