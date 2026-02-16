"""
DiseaseOntology_get_term

Get detailed information about a disease from the Disease Ontology (DO) by its DOID identifier. R...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DiseaseOntology_get_term(
    doid: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a disease from the Disease Ontology (DO) by its DOID identifier. R...

    Parameters
    ----------
    doid : str
        Disease Ontology identifier in format 'DOID:XXXX'. Examples: 'DOID:162' (canc...
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

    return get_shared_client().run_one_function(
        {"name": "DiseaseOntology_get_term", "arguments": {"doid": doid}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DiseaseOntology_get_term"]
