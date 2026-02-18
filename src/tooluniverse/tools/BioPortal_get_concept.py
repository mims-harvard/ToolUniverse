"""
BioPortal_get_concept

Get detailed information about a specific concept from a BioPortal ontology, including full defin...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioPortal_get_concept(
    ontology: str,
    concept_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a specific concept from a BioPortal ontology, including full defin...

    Parameters
    ----------
    ontology : str
        Ontology acronym in BioPortal. Examples: 'GO', 'HP', 'DOID', 'CHEBI', 'UBERON...
    concept_id : str
        Full IRI of the concept. Examples: 'http://purl.obolibrary.org/obo/DOID_1909'...
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
        {
            "name": "BioPortal_get_concept",
            "arguments": {"ontology": ontology, "concept_id": concept_id},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioPortal_get_concept"]
