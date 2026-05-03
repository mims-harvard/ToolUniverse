"""
NCBI_search_nucleotide

Search NCBI Nucleotide database (GenBank/EMBL/RefSeq) by organism, gene name, or keywords. Return...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCBI_search_nucleotide(
    operation: Optional[str] = None,
    organism: Optional[str] = None,
    gene: Optional[str] = None,
    strain: Optional[str] = None,
    keywords: Optional[str] = None,
    seq_type: Optional[str] = None,
    query: Optional[str] = None,
    limit: Optional[int] = 20,
    sort: Optional[str] = "relevance",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search NCBI Nucleotide database (GenBank/EMBL/RefSeq) by organism, gene name, or keywords. Return...

    Parameters
    ----------
    operation : str
        Operation type (fixed: search)
    organism : str
        Organism name to search (e.g., 'Escherichia coli', 'Homo sapiens'). Searches ...
    gene : str
        Gene name to search (e.g., 'BRCA1', 'TP53'). Searches in [Gene] field.
    strain : str
        Strain name to filter (e.g., 'K-12', 'MG1655'). Searches in [Strain] field.
    keywords : str
        Keywords to search in titles (e.g., 'complete genome', 'mitochondrial'). Sear...
    seq_type : str
        Sequence type filter: 'complete_genome' for complete genomes, 'mrna' for mRNA...
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
            "organism": organism,
            "gene": gene,
            "strain": strain,
            "keywords": keywords,
            "seq_type": seq_type,
            "query": query,
            "limit": limit,
            "sort": sort,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NCBI_search_nucleotide",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCBI_search_nucleotide"]
