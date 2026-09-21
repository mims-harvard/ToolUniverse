"""
GO_get_genes_for_term

Finds genes/proteins annotated to a Gene Ontology term, including annotations to its descendant t...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GO_get_genes_for_term(
    id: str,
    taxon: Optional[str] = None,
    rows: Optional[int] = 100,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Finds genes/proteins annotated to a Gene Ontology term, including annotations to its descendant t...

    Parameters
    ----------
    id : str
        The standard GO term ID, e.g., 'GO:0006915'.
    taxon : str
        Optional species filter using an NCBI taxon ID, e.g. 'NCBITaxon:9606' (human)...
    rows : int
        Maximum number of annotation rows to scan. Distinct genes returned may be few...
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
        for k, v in {"id": id, "taxon": taxon, "rows": rows}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GO_get_genes_for_term",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GO_get_genes_for_term"]
