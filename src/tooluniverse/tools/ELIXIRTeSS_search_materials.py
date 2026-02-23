"""
ELIXIRTeSS_search_materials

Search ELIXIR TeSS (Training eSupport System) for bioinformatics and life science training materi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ELIXIRTeSS_search_materials(
    q: Optional[str | Any] = None,
    scientific_topics: Optional[str | Any] = None,
    target_audience: Optional[str | Any] = None,
    difficulty_level: Optional[str | Any] = None,
    licence: Optional[str | Any] = None,
    page_size: Optional[int | Any] = None,
    page: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search ELIXIR TeSS (Training eSupport System) for bioinformatics and life science training materi...

    Parameters
    ----------
    q : str | Any
        Search query for training materials. Examples: 'CRISPR', 'protein structure p...
    scientific_topics : str | Any
        Filter by EDAM scientific topic. Examples: 'Genomics', 'Proteomics', 'Sequenc...
    target_audience : str | Any
        Filter by target audience. Examples: 'Researchers', 'Graduate students', 'Bio...
    difficulty_level : str | Any
        Filter by difficulty: 'Beginner', 'Intermediate', 'Advanced'
    licence : str | Any
        Filter by license type. Example: 'CC-BY'
    page_size : int | Any
        Number of results to return (default 10, max 100)
    page : int | Any
        Page number for pagination
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
            "name": "ELIXIRTeSS_search_materials",
            "arguments": {
                "q": q,
                "scientific_topics": scientific_topics,
                "target_audience": target_audience,
                "difficulty_level": difficulty_level,
                "licence": licence,
                "page_size": page_size,
                "page": page,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ELIXIRTeSS_search_materials"]
