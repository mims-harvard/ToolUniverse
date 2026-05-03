"""
OxO_search_ontology_mappings

Search for cross-reference mappings for multiple ontology terms at once using the EBI OxO service...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OxO_search_ontology_mappings(
    term_ids: str,
    distance: Optional[int] = 1,
    target_prefix: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search for cross-reference mappings for multiple ontology terms at once using the EBI OxO service...

    Parameters
    ----------
    term_ids : str
        Comma-separated list of ontology term IDs to map. Examples: 'HP:0001250,HP:00...
    distance : int
        Maximum mapping distance (1-3). Default: 1.
    target_prefix : str
        Filter mappings to a specific ontology prefix. Examples: 'MeSH' (Medical Subj...
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
            "term_ids": term_ids,
            "distance": distance,
            "target_prefix": target_prefix,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OxO_search_ontology_mappings",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OxO_search_ontology_mappings"]
