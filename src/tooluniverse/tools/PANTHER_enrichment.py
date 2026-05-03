"""
PANTHER_enrichment

Perform gene set enrichment (overrepresentation) analysis using PANTHER. Given a gene list, ident...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PANTHER_enrichment(
    gene_list: str,
    organism: Optional[int | Any] = None,
    annotation_dataset: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Perform gene set enrichment (overrepresentation) analysis using PANTHER. Given a gene list, ident...

    Parameters
    ----------
    gene_list : str
        Comma-separated list of gene symbols, UniProt IDs, or Ensembl IDs. Example: '...
    organism : int | Any
        NCBI taxonomy ID. Default: 9606 (human). Others: 10090 (mouse), 7227 (fly), 5...
    annotation_dataset : str | Any
        Annotation dataset for enrichment. Options: 'GO:0008150' (biological_process,...
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
