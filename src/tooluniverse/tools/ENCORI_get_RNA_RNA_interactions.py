"""
ENCORI_get_RNA_RNA_interactions

Retrieve ncRNA-RNA (RNA-RNA duplex) interaction networks from high-throughput crosslinking (PARIS...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ENCORI_get_RNA_RNA_interactions(
    rna: Optional[str] = None,
    assembly: Optional[str] = None,
    gene_type: Optional[str] = None,
    interaction_min: Optional[int] = None,
    exp_min: Optional[int] = None,
    cell_type: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve ncRNA-RNA (RNA-RNA duplex) interaction networks from high-throughput crosslinking (PARIS...

    Parameters
    ----------
    rna : str
        RNA symbol whose duplex partners are wanted, e.g. 'MALAT1', 'NEAT1' (aliases:...
    assembly : str
        Genome assembly (default 'hg38').
    gene_type : str
        Biotype of the query RNA: 'lncRNA' (default), 'mRNA', 'pseudogene', 'sncRNA',...
    interaction_min : int
        Minimum interaction count (default 1).
    exp_min : int
        Minimum number of supporting experiments (default 1).
    cell_type : str
        Restrict to a cell line/tissue (default 'all').
    limit : int
        Maximum interaction rows to return (1-500, default 100).
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
            "rna": rna,
            "assembly": assembly,
            "gene_type": gene_type,
            "interaction_min": interaction_min,
            "exp_min": exp_min,
            "cell_type": cell_type,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ENCORI_get_RNA_RNA_interactions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ENCORI_get_RNA_RNA_interactions"]
