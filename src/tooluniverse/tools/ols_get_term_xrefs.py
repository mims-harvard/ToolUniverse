"""
ols_get_term_xrefs

Get the cross-references (obo_xref) of an ontology term in OLS — the canonical OxO-replacement ID...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ols_get_term_xrefs(
    operation: Optional[str] = None,
    id: Optional[str] = None,
    term_id: Optional[str] = None,
    obo_id: Optional[str] = None,
    term_iri: Optional[str] = None,
    ontology: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the cross-references (obo_xref) of an ontology term in OLS — the canonical OxO-replacement ID...

    Parameters
    ----------
    operation : str
        The operation to perform (get_term_xrefs)
    id : str
        Ontology term CURIE (e.g. 'EFO:0004611', 'MONDO:0005148', 'UBERON:0002107').
    term_id : str
        Alias for id — ontology term CURIE (e.g. 'MONDO:0005148').
    obo_id : str
        Alias for id — OBO-style term identifier (e.g. 'EFO:0004611').
    term_iri : str
        Alias for id — may also pass a full IRI/short-form term identifier.
    ontology : str
        Ontology ID (e.g. 'efo', 'mondo', 'go'). Auto-inferred from the term CURIE pr...
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
            "operation": operation,
            "id": id,
            "term_id": term_id,
            "obo_id": obo_id,
            "term_iri": term_iri,
            "ontology": ontology,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ols_get_term_xrefs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ols_get_term_xrefs"]
