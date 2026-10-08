"""
NCATSTranslator_query_associations

One-hop biolink association query across ~15 NCATS Translator knowledge providers via the Aragorn...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCATSTranslator_query_associations(
    entity_id: str,
    target_category: str,
    predicate: str,
    target_role: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    One-hop biolink association query across ~15 NCATS Translator knowledge providers via the Aragorn...

    Parameters
    ----------
    entity_id : str
        Translator-normalized CURIE of the known entity, e.g. 'MONDO:0004975'. Use NC...
    target_category : str
        Biolink category to search for, e.g. 'ChemicalEntity', 'Gene', 'Disease', 'Ph...
    predicate : str
        Biolink predicate linking the two, e.g. 'treats', 'gene_associated_with_condi...
    target_role : str
        Whether the target (unknown) entity is the predicate's subject or object: 'su...
    limit : int
        Max results to return, 1-100. Default 25.
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
            "entity_id": entity_id,
            "target_category": target_category,
            "predicate": predicate,
            "target_role": target_role,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NCATSTranslator_query_associations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCATSTranslator_query_associations"]
