"""
SRA_search_experiments

Search the NCBI Sequence Read Archive (SRA) for sequencing experiments by keyword, organism, libr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SRA_search_experiments(
    query: Optional[str] = None,
    organism: Optional[str] = None,
    library_strategy: Optional[str] = None,
    platform: Optional[str] = None,
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the NCBI Sequence Read Archive (SRA) for sequencing experiments by keyword, organism, libr...

    Parameters
    ----------
    query : str
        Search keywords (e.g., 'human gut metagenome', 'BRCA1 RNA-Seq', 'single cell ...
    organism : str
        Organism name to filter by (e.g., 'Homo sapiens', 'Mus musculus', 'human gut ...
    library_strategy : str
        Sequencing strategy filter (e.g., 'RNA-Seq', 'WGS', 'WXS', 'ChIP-Seq', 'ATAC-...
    platform : str
        Sequencing platform filter (e.g., 'ILLUMINA', 'PACBIO_SMRT', 'OXFORD_NANOPORE...
    limit : int
        Maximum results to return (1-50, default 10)
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
            "query": query,
            "organism": organism,
            "library_strategy": library_strategy,
            "platform": platform,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SRA_search_experiments",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SRA_search_experiments"]
