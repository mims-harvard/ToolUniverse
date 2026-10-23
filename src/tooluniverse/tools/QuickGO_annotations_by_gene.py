"""
QuickGO_annotations_by_gene

Search Gene Ontology (GO) annotations for a specific gene product using the EBI QuickGO browser. ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def QuickGO_annotations_by_gene(
    gene_product_id: str,
    aspect: Optional[str] = None,
    taxon_id: Optional[int] = None,
    limit: Optional[int] = 25,
    page: Optional[int] = 1,
    evidence_code: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search Gene Ontology (GO) annotations for a specific gene product using the EBI QuickGO browser. ...

    Parameters
    ----------
    gene_product_id : str
        Gene product identifier, typically a UniProtKB accession. Format: 'UniProtKB:...
    aspect : str
        Filter by GO aspect: 'biological_process', 'molecular_function', or 'cellular...
    taxon_id : int
        Filter by NCBI taxonomy ID. Example: 9606 (human), 10090 (mouse).
    limit : int
        Number of annotations per page. Default: 25, max: 100.
    page : int
        One-based result page. Use metadata.next_page while metadata.has_more is true.
    evidence_code : str
        Exact Evidence and Conclusion Ontology (ECO) accession filter, such as 'ECO:0...
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
            "gene_product_id": gene_product_id,
            "aspect": aspect,
            "taxon_id": taxon_id,
            "limit": limit,
            "page": page,
            "evidence_code": evidence_code,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "QuickGO_annotations_by_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["QuickGO_annotations_by_gene"]
