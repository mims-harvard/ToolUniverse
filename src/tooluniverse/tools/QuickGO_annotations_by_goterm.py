"""
QuickGO_annotations_by_goterm

Search for all gene products annotated with a specific Gene Ontology (GO) term using the EBI Quic...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def QuickGO_annotations_by_goterm(
    go_id: str,
    taxon_id: Optional[int | Any] = None,
    limit: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for all gene products annotated with a specific Gene Ontology (GO) term using the EBI Quic...

    Parameters
    ----------
    go_id : str
        Gene Ontology term accession. Examples: 'GO:0006915' (apoptotic process), 'GO...
    taxon_id : int | Any
        Filter by NCBI taxonomy ID. Example: 9606 (human), 10090 (mouse), 7227 (fly).
    limit : int
        Maximum number of annotations to return. Default: 25, max: 100.
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
        for k, v in {"go_id": go_id, "taxon_id": taxon_id, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "QuickGO_annotations_by_goterm",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["QuickGO_annotations_by_goterm"]
