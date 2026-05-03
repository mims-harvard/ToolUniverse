"""
ImmPort_search_studies

Search the ImmPort immunology database for studies by keyword, disease condition, assay method, o...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ImmPort_search_studies(
    query: str,
    condition_or_disease: Optional[str] = None,
    assay_method: Optional[str] = None,
    research_focus: Optional[str] = None,
    species: Optional[str] = None,
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search the ImmPort immunology database for studies by keyword, disease condition, assay method, o...

    Parameters
    ----------
    query : str
        Search keywords (e.g., 'influenza vaccine', 'COVID-19', 'T cell response', 'm...
    condition_or_disease : str
        Filter by disease/condition (e.g., 'influenza', 'malaria', 'HIV', 'dengue', '...
    assay_method : str
        Filter by assay method (e.g., 'Flow Cytometry', 'ELISPOT', 'RNA sequencing', ...
    research_focus : str
        Filter by research focus (e.g., 'Vaccine Response', 'Infection Response', 'Im...
    species : str
        Filter by species (e.g., 'Homo sapiens', 'Mus musculus'). Applied server-side.
    limit : int
        Maximum number of studies to return (1-100, default 10)
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
    _args = {
        k: v
        for k, v in {
            "query": query,
            "condition_or_disease": condition_or_disease,
            "assay_method": assay_method,
            "research_focus": research_focus,
            "species": species,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ImmPort_search_studies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ImmPort_search_studies"]
