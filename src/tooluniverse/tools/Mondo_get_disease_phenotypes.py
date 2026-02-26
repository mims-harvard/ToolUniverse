"""
Mondo_get_disease_phenotypes

Get HPO (Human Phenotype Ontology) phenotypes associated with a Mondo disease. Returns the phenot...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Mondo_get_disease_phenotypes(
    disease_id: str,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get HPO (Human Phenotype Ontology) phenotypes associated with a Mondo disease. Returns the phenot...

    Parameters
    ----------
    disease_id : str
        Mondo disease identifier. Examples: 'MONDO:0004975' (Alzheimer disease, 95 ph...
    limit : int
        Maximum number of phenotypes to return (default: 20, max: 200).
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
            "name": "Mondo_get_disease_phenotypes",
            "arguments": {"disease_id": disease_id, "limit": limit},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Mondo_get_disease_phenotypes"]
