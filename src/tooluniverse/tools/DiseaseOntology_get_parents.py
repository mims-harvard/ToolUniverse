"""
DiseaseOntology_get_parents

Get the parent disease terms for a Disease Ontology term, enabling navigation of the disease hier...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DiseaseOntology_get_parents(
    doid: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the parent disease terms for a Disease Ontology term, enabling navigation of the disease hier...

    Parameters
    ----------
    doid : str
        Disease Ontology identifier in format 'DOID:XXXX'. Examples: 'DOID:10283' (pr...
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
    _args = {k: v for k, v in {"doid": doid}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "DiseaseOntology_get_parents",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DiseaseOntology_get_parents"]
