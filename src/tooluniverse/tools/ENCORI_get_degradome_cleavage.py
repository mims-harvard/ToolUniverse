"""
ENCORI_get_degradome_cleavage

Retrieve miRNA cleavage sites validated by degradome-seq (PARE / Degradome) via ENCORI (starBase)...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ENCORI_get_degradome_cleavage(
    gene: Optional[str] = None,
    mirna: Optional[str] = None,
    assembly: Optional[str] = None,
    gene_type: Optional[str] = None,
    degradome_exp_min: Optional[int] = None,
    clip_min: Optional[int] = None,
    cell_type: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve miRNA cleavage sites validated by degradome-seq (PARE / Degradome) via ENCORI (starBase)...

    Parameters
    ----------
    gene : str
        Target gene symbol to get cleaving miRNAs for, e.g. 'TP53' (alias: 'gene_symb...
    mirna : str
        miRNA name to get cleavage targets for, e.g. 'hsa-miR-1-3p'. Mutually exclusi...
    assembly : str
        Genome assembly (default 'hg19' — the only assembly with degradome data; hg38...
    gene_type : str
        Target biotype: 'mRNA' (default), 'lncRNA', 'pseudogene', 'sncRNA'.
    degradome_exp_min : int
        Minimum number of supporting degradome experiments (default 1).
    clip_min : int
        Minimum number of supporting CLIP experiments (default 1).
    cell_type : str
        Restrict to a cell line/tissue (default 'all').
    limit : int
        Maximum cleavage rows to return (1-500, default 100).
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
            "mirna": mirna,
            "assembly": assembly,
            "gene_type": gene_type,
            "degradome_exp_min": degradome_exp_min,
            "clip_min": clip_min,
            "cell_type": cell_type,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ENCORI_get_degradome_cleavage",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ENCORI_get_degradome_cleavage"]
