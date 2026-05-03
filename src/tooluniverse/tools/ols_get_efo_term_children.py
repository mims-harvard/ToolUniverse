"""
ols_get_efo_term_children

List children of an EFO term (ontology hierarchy). Provide `iri` or `obo_id`.

Tip: use `ols_sear...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ols_get_efo_term_children(
    iri: Optional[str] = None,
    obo_id: Optional[str] = None,
    size: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
        List children of an EFO term (ontology hierarchy). Provide `iri` or `obo_id`.

    Tip: use `ols_sear...

        Parameters
        ----------
        iri : str
            Term IRI returned by `ols_search_efo_terms`.
        obo_id : str
            OBO ID like 'EFO:0000400' (will be converted to an EFO IRI).
        size : int
            Maximum number of children to return.
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
        for k, v in {"iri": iri, "obo_id": obo_id, "size": size}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ols_get_efo_term_children",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ols_get_efo_term_children"]
