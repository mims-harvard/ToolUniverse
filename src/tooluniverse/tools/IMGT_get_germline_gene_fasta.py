"""
IMGT_get_germline_gene_fasta

Retrieve IMGT germline immunoglobulin (IG) / T-cell-receptor (TR) gene reference sequences in FAS...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IMGT_get_germline_gene_fasta(
    operation: Optional[str] = None,
    gene_type: Optional[str] = None,
    gene: Optional[str] = None,
    species: Optional[str] = "Homo sapiens",
    label: Optional[str] = "7.2",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve IMGT germline immunoglobulin (IG) / T-cell-receptor (TR) gene reference sequences in FAS...

    Parameters
    ----------
    operation : str

    gene_type : str
        IG/TR gene type/locus: IGHV, IGHD, IGHJ, IGKV, IGLV, TRAV, TRBV, TRBD, TRBJ, ...
    gene : str
        Alias for gene_type.
    species : str
        Species name (default: Homo sapiens). Examples: 'Mus musculus', 'Homo sapiens'.
    label : str
        IMGT GENElect label controlling the region set (default '7.2' = all V/D/J-REG...
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
            "operation": operation,
            "gene_type": gene_type,
            "gene": gene,
            "species": species,
            "label": label,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "IMGT_get_germline_gene_fasta",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IMGT_get_germline_gene_fasta"]
