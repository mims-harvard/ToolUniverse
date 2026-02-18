"""
BioPortal_get_hierarchy

Get children, parents, or ancestors of a specific concept in a BioPortal ontology. Enables hierar...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioPortal_get_hierarchy(
    ontology: str,
    concept_id: str,
    direction: Optional[str | Any] = None,
    page_size: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get children, parents, or ancestors of a specific concept in a BioPortal ontology. Enables hierar...

    Parameters
    ----------
    ontology : str
        Ontology acronym in BioPortal. Examples: 'GO', 'HP', 'DOID', 'CHEBI', 'UBERON...
    concept_id : str
        Full IRI of the concept. Example: 'http://purl.obolibrary.org/obo/DOID_9351' ...
    direction : str | Any
        Direction of hierarchy traversal: 'children' (narrower terms, default), 'pare...
    page_size : int | Any
        Number of results to return (default: 25, max: 100).
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
            "name": "BioPortal_get_hierarchy",
            "arguments": {
                "ontology": ontology,
                "concept_id": concept_id,
                "direction": direction,
                "page_size": page_size,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioPortal_get_hierarchy"]
