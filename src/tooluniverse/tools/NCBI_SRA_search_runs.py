"""
NCBI_SRA_search_runs

Search NCBI Sequence Read Archive (SRA) for NGS/RNA-seq sequencing runs by study accession, organ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCBI_SRA_search_runs(
    operation: Optional[str] = None,
    study: Optional[str] = None,
    organism: Optional[str] = None,
    strategy: Optional[str] = None,
    platform: Optional[str] = None,
    source: Optional[str] = None,
    query: Optional[str] = None,
    limit: Optional[int] = 20,
    sort: Optional[str] = "relevance",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search NCBI Sequence Read Archive (SRA) for NGS/RNA-seq sequencing runs by study accession, organ...

    Parameters
    ----------
    operation : str
        Operation type (fixed: search)
    study : str
        Study accession to search (e.g., 'SRP000001', 'ERP000001', 'DRP000001'). Sear...
    organism : str
        Organism name to filter (e.g., 'Homo sapiens', 'Mus musculus', 'SARS-CoV-2')....
    strategy : str
        Sequencing strategy to filter. Common values: 'RNA-Seq' (transcriptomics), 'W...
    platform : str
        Sequencing platform to filter. Common values: 'ILLUMINA', 'OXFORD_NANOPORE', ...
    source : str
        Library source to filter. Common values: 'GENOMIC' (DNA), 'TRANSCRIPTOMIC' (R...
    query : str
        Free-form search query if not using structured filters. Use NCBI query syntax...
    limit : int
        Maximum number of results to return (default: 20, max: 100)
    sort : str
        Sort order for results (default: relevance)
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "study": study,
            "organism": organism,
            "strategy": strategy,
            "platform": platform,
            "source": source,
            "query": query,
            "limit": limit,
            "sort": sort,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NCBI_SRA_search_runs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCBI_SRA_search_runs"]
