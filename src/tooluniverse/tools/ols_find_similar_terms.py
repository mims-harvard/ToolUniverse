"""
ols_find_similar_terms

Find similar terms using LLM-based similarity
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ols_find_similar_terms(
    ontology: str,
    operation: Optional[str] = None,
    term_iri: Optional[str] = None,
    size: Optional[int] = 10,
    term_id: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Find similar terms using LLM-based similarity

    Parameters
    ----------
    operation : str
        The operation to perform (find_similar_terms)
    term_iri : str
        The IRI of the term to find similar terms for
    ontology : str
        The ontology ID
    size : int
        Number of similar terms to return (default: 10)
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
            "size": size,
            "term_id": term_id,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ols_find_similar_terms",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ols_find_similar_terms"]
