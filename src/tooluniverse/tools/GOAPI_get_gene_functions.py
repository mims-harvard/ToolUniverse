"""
GOAPI_get_gene_functions

Get Gene Ontology (GO) annotations for a specific gene, showing its known biological processes, m...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GOAPI_get_gene_functions(
    gene_id: str,
    rows: Optional[int] = None,
    aspect: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get Gene Ontology (GO) annotations for a specific gene, showing its known biological processes, m...

    Parameters
    ----------
    gene_id : str
        Gene identifier as a CURIE. Examples: 'HGNC:11998' (TP53), 'UniProtKB:P04637'...
    rows : int
        Maximum number of annotations to return (default: 20, max: 100).
    aspect : str
        Filter by GO aspect: 'P' (Biological Process), 'F' (Molecular Function), 'C' ...
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
        for k, v in {"gene_id": gene_id, "rows": rows, "aspect": aspect}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GOAPI_get_gene_functions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GOAPI_get_gene_functions"]
