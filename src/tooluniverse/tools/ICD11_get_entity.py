"""
ICD11_get_entity

Get detailed information about an ICD-11 disease entity by its unique identifier or code. Returns...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ICD11_get_entity(
    entity_id: str,
    linearization: Optional[str] = "mms",
    language: Optional[str] = "en",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about an ICD-11 disease entity by its unique identifier or code. Returns...

    Parameters
    ----------
    entity_id : str
        ICD-11 entity ID (e.g., '1435254666' for diabetes mellitus) or full URI
    linearization : str
        ICD-11 linearization (default: 'mms')
    language : str
        Language for results (ISO 639-1 code)
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
            "entity_id": entity_id,
            "linearization": linearization,
            "language": language,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ICD11_get_entity",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ICD11_get_entity"]
