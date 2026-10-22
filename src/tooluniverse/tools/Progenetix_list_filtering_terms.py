"""
Progenetix_list_filtering_terms

List Progenetix filtering terms (ontology codes) with matching-sample counts. Prefix filtering is...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Progenetix_list_filtering_terms(
    prefixes: Optional[str] = "NCIT",
    limit: Optional[int] = 25,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    List Progenetix filtering terms (ontology codes) with matching-sample counts. Prefix filtering is...

    Parameters
    ----------
    prefixes : str
        Ontology prefix to filter terms by. Use 'NCIT' for NCI Thesaurus cancer types...
    limit : int
        Maximum number of terms to return (default: 25).
    offset : int
        Zero-based offset after prefix filtering. Continue with data.next_offset.
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
        for k, v in {"prefixes": prefixes, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Progenetix_list_filtering_terms",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Progenetix_list_filtering_terms"]
