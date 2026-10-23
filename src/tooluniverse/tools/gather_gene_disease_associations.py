"""
gather_gene_disease_associations

Query multiple gene-disease databases (DisGeNET, OMIM, OpenTargets, GenCC, ClinVar) in a single c...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def gather_gene_disease_associations(
    gene: Optional[str] = None,
    disease: Optional[str] = None,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    source_limit: Optional[int] = 10,
    source_offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Query multiple gene-disease databases (DisGeNET, OMIM, OpenTargets, GenCC, ClinVar) in a single c...

    Parameters
    ----------
    gene : str
        Gene symbol (e.g., 'TP53', 'BRCA1'). At least one of gene or disease required.
    disease : str
        Disease name (e.g., 'breast cancer', 'distal renal tubular acidosis'). At lea...
    limit : int
        Associations per page (1-500; default 50).
    offset : int
        Zero-based concordance association offset.
    source_limit : int
        Rows returned per source (1-500; default 10).
    source_offset : int
        Zero-based offset applied independently to every source list.
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
            "gene": gene,
            "disease": disease,
            "limit": limit,
            "offset": offset,
            "source_limit": source_limit,
            "source_offset": source_offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "gather_gene_disease_associations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["gather_gene_disease_associations"]
