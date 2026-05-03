"""
ensembl_get_ontology_term

Get detailed information about a specific ontology term (GO, SO, HPO). Returns term name, definit...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ensembl_get_ontology_term(
    id: str,
    relation: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about a specific ontology term (GO, SO, HPO). Returns term name, definit...

    Parameters
    ----------
    id : str
        Ontology term ID (e.g., 'GO:0005737', 'SO:0000704', 'HP:0001250')
    relation : str
        Filter relationships (optional, e.g., 'is_a', 'part_of', 'regulates')
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
    _args = {k: v for k, v in {"id": id, "relation": relation}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ensembl_get_ontology_term",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ensembl_get_ontology_term"]
