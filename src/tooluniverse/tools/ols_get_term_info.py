"""
ols_get_term_info

Get detailed information about a specific term in OLS
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ols_get_term_info(
    operation: Optional[str] = None,
    id: Optional[str] = None,
    term_id: Optional[str] = None,
    term_iri: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about a specific term in OLS

    Parameters
    ----------
    operation : str
        The operation to perform (get_term_info)
    id : str
        Ontology term ID or IRI (e.g. HP:0001903, http://purl.obolibrary.org/obo/HP_0...
    term_id : str
        Alias for id — ontology term ID (e.g. HP:0001903)
    term_iri : str
        Alias for id. Full IRI or short-form ID (e.g., GO:0008150, EFO:0003971). Same...
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
            "id": id,
            "term_id": term_id,
            "term_iri": term_iri,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ols_get_term_info",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ols_get_term_info"]
