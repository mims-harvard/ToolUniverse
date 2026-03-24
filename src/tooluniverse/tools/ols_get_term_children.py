"""
ols_get_term_children

Get child terms of a specific term in an ontology
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ols_get_term_children(
    ontology: str,
    operation: Optional[str] = None,
    term_iri: Optional[str] = None,
    include_obsolete: Optional[bool] = False,
    size: Optional[int] = 20,
    term_id: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get child terms of a specific term in an ontology

    Parameters
    ----------
    operation : str
        The operation to perform (get_term_children)
    term_iri : str
        The IRI of the term to retrieve children for
    ontology : str
        The ontology ID
    include_obsolete : bool
        Include obsolete terms (default: false)
    size : int
        Number of results to return (default: 20)
    term_id : str
        Alias for term_iri. Short-form ontology ID (e.g., GO:0008150) or full IRI.
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
            "term_iri": term_iri,
            "ontology": ontology,
            "include_obsolete": include_obsolete,
            "size": size,
            "term_id": term_id,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ols_get_term_children",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ols_get_term_children"]
