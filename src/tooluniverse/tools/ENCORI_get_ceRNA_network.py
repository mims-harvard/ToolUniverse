"""
ENCORI_get_ceRNA_network

Build competing-endogenous-RNA (ceRNA / miRNA-sponge) networks via ENCORI (starBase) ceRNA module...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ENCORI_get_ceRNA_network(
    gene: Optional[str] = None,
    assembly: Optional[str] = None,
    gene_type: Optional[str] = None,
    shared_mirna_min: Optional[int] = None,
    pval: Optional[float] = None,
    fdr: Optional[float] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Build competing-endogenous-RNA (ceRNA / miRNA-sponge) networks via ENCORI (starBase) ceRNA module...

    Parameters
    ----------
    gene : str
        Query gene or lncRNA symbol whose ceRNA partners are wanted, e.g. 'PTEN', 'MA...
    assembly : str
        Genome assembly (default 'hg38').
    gene_type : str
        Biotype of the query gene: 'mRNA' (default), 'lncRNA', 'pseudogene', 'sncRNA'.
    shared_mirna_min : int
        Minimum number of shared miRNA families required (default 5).
    pval : float
        Maximum hypergeometric p-value (default 0.01).
    fdr : float
        Maximum FDR (default 0.01).
    limit : int
        Maximum ceRNA partner rows to return (1-500, default 100).
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
            "assembly": assembly,
            "gene_type": gene_type,
            "shared_mirna_min": shared_mirna_min,
            "pval": pval,
            "fdr": fdr,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ENCORI_get_ceRNA_network",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ENCORI_get_ceRNA_network"]
