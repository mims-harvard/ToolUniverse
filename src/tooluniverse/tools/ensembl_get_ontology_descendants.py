"""
ensembl_get_ontology_descendants

WARNING (checked 2026-09-21): Ensembl's REST server currently answers this endpoint with the term...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ensembl_get_ontology_descendants(
    id: str,
    closest_term: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    WARNING (checked 2026-09-21): Ensembl's REST server currently answers this endpoint with the term...

    Parameters
    ----------
    id : str
        GO term ID (e.g., 'GO:0005737' for cytoplasm)
    closest_term : bool
        Return only immediate children
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"id": id, "closest_term": closest_term}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ensembl_get_ontology_descendants",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ensembl_get_ontology_descendants"]
