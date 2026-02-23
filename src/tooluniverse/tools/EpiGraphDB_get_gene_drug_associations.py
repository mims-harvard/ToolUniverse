"""
EpiGraphDB_get_gene_drug_associations

Get pharmacogenomics drug-gene associations from CPIC and PharmGKB databases via EpiGraphDB. Retu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EpiGraphDB_get_gene_drug_associations(
    gene_name: str,
    pval_threshold: Optional[float] = 0.05,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get pharmacogenomics drug-gene associations from CPIC and PharmGKB databases via EpiGraphDB. Retu...

    Parameters
    ----------
    gene_name : str
        Gene symbol to find drug associations for (e.g., 'TP53', 'EGFR', 'DPYD', 'CYP...
    pval_threshold : float
        P-value threshold (default 0.05).
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

    return get_shared_client().run_one_function(
        {
            "name": "EpiGraphDB_get_gene_drug_associations",
            "arguments": {"gene_name": gene_name, "pval_threshold": pval_threshold},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EpiGraphDB_get_gene_drug_associations"]
