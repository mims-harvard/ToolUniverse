"""
ENCORI_get_RBP_targets

Look up RBP-RNA binding sites from CLIP-seq via ENCORI (starBase) RBPTarget module. Provide 'rbp'...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ENCORI_get_RBP_targets(
    rbp: Optional[str] = None,
    gene: Optional[str] = None,
    assembly: Optional[str] = None,
    gene_type: Optional[str] = None,
    clip_min: Optional[int] = None,
    pancancer_min: Optional[int] = None,
    cell_type: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Look up RBP-RNA binding sites from CLIP-seq via ENCORI (starBase) RBPTarget module. Provide 'rbp'...

    Parameters
    ----------
    rbp : str
        RNA-binding protein symbol to get targets for, e.g. 'PTBP1', 'ELAVL1' (alias:...
    gene : str
        Gene/transcript symbol to get binding RBPs for, e.g. 'TP53', 'MYC' (alias: 'g...
    assembly : str
        Genome assembly (default 'hg38'; use 'hg19' for the older build).
    gene_type : str
        Transcript biotype to query: 'mRNA' (default), 'lncRNA', 'pseudogene', 'sncRN...
    clip_min : int
        Minimum number of supporting CLIP-seq experiments (default 1).
    pancancer_min : int
        Minimum pan-cancer support count (default 0).
    cell_type : str
        Restrict to a CLIP cell line/tissue (default 'all').
    limit : int
        Maximum binding rows to return (1-500, default 100).
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
            "rbp": rbp,
            "gene": gene,
            "assembly": assembly,
            "gene_type": gene_type,
            "clip_min": clip_min,
            "pancancer_min": pancancer_min,
            "cell_type": cell_type,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ENCORI_get_RBP_targets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ENCORI_get_RBP_targets"]
