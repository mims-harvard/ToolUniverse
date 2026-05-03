"""
ICD11_search_diseases

Search ICD-11 for diseases by name, symptoms, or clinical terms. ICD-11 is the WHO's 11th revisio...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ICD11_search_diseases(
    query: str,
    linearization: Optional[str] = "mms",
    flatResults: Optional[bool] = True,
    useFlexisearch: Optional[bool] = True,
    language: Optional[str] = "en",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search ICD-11 for diseases by name, symptoms, or clinical terms. ICD-11 is the WHO's 11th revisio...

    Parameters
    ----------
    query : str
        Search query (disease name, symptom, or clinical term, e.g., 'diabetes mellit...
    linearization : str
        ICD-11 linearization to search (default: 'mms' for mortality/morbidity statis...
    flatResults : bool
        Return flat list of results (true) or hierarchical structure (false)
    useFlexisearch : bool
        Use flexible search algorithm for better matching
    language : str
        Language for results (ISO 639-1 code, e.g., 'en', 'es', 'fr', 'zh')
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "query": query,
            "linearization": linearization,
            "flatResults": flatResults,
            "useFlexisearch": useFlexisearch,
            "language": language,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ICD11_search_diseases",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ICD11_search_diseases"]
