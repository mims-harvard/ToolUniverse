"""
PANTHER_enrichment

Perform gene set enrichment (overrepresentation) analysis using PANTHER. Returns only statistical...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PANTHER_enrichment(
    gene_list: str,
    organism: Optional[int] = None,
    annotation_dataset: Optional[str] = None,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Perform gene set enrichment (overrepresentation) analysis using PANTHER. Returns only statistical...

    Parameters
    ----------
    gene_list : str
        Comma-separated list of gene symbols, UniProt IDs, or Ensembl IDs. Example: '...
    organism : int
        NCBI taxonomy ID. Default: 9606 (human). Others: 10090 (mouse), 7227 (fly), 5...
    annotation_dataset : str
        Annotation dataset for enrichment. Options: 'GO:0008150' (biological_process,...
    limit : int
        Maximum significant terms per page (default 50, max 1000).
    offset : int
        Zero-based offset in the FDR-sorted significant terms. Continue with next_off...
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
            "gene_list": gene_list,
            "organism": organism,
            "annotation_dataset": annotation_dataset,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PANTHER_enrichment",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PANTHER_enrichment"]
