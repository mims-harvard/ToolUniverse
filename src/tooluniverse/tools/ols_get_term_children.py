"""
ols_get_term_children

Get child terms of a specific term in an ontology. Use `term_id` with CURIE format (e.g., 'HP:000...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ols_get_term_children(
    operation: Optional[str] = None,
    term_iri: Optional[str] = None,
    term_id: Optional[str] = None,
    ontology: Optional[str] = None,
    include_obsolete: Optional[bool] = False,
    size: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get child terms of a specific term in an ontology. Use `term_id` with CURIE format (e.g., 'HP:000...

    Parameters
    ----------
    operation : str
        The operation to perform (get_term_children)
    term_iri : str
        The full IRI of the term (e.g., http://www.ebi.ac.uk/efo/EFO_0000408)
    term_id : str
        Short-form CURIE (e.g., 'HP:0001928', 'GO:0008150'). Ontology is auto-inferre...
    ontology : str
        Ontology ID (e.g., 'hp', 'go', 'efo'). Auto-inferred from term_id prefix when...
    include_obsolete : bool
        Include obsolete terms (default: false)
    size : int
        Number of results to return (default: 20)
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
            "term_id": term_id,
            "ontology": ontology,
            "include_obsolete": include_obsolete,
            "size": size,
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
