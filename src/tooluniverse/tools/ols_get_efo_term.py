"""
ols_get_efo_term

Get details for a single EFO term by `iri` (recommended) or `obo_id` (e.g., 'EFO:0000400'). Use `...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ols_get_efo_term(
    iri: Optional[str] = None,
    obo_id: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get details for a single EFO term by `iri` (recommended) or `obo_id` (e.g., 'EFO:0000400'). Use `...

    Parameters
    ----------
    iri : str
        Term IRI returned by `ols_search_efo_terms`.
    obo_id : str
        OBO ID like 'EFO:0000400' (will be converted to an EFO IRI).
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
    _args = {k: v for k, v in {"iri": iri, "obo_id": obo_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ols_get_efo_term",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ols_get_efo_term"]
