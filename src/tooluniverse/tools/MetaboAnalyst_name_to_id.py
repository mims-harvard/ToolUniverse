"""
MetaboAnalyst_name_to_id

Map metabolite common names to database identifiers (KEGG, HMDB, PubChem, ChEBI). Resolves metabo...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MetaboAnalyst_name_to_id(
    metabolites: list[str],
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Map metabolite common names to database identifiers (KEGG, HMDB, PubChem, ChEBI). Resolves metabo...

    Parameters
    ----------
    metabolites : list[str]
        List of metabolite common names to map. Example: ['glucose', 'pyruvate', 'lac...
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
    _args = {k: v for k, v in {
        "metabolites": metabolites
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "MetaboAnalyst_name_to_id",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["MetaboAnalyst_name_to_id"]
