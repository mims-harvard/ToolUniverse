"""
ICD11_browse_hierarchy

Navigate the ICD-11 disease classification hierarchy by retrieving child entities of a parent cat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ICD11_browse_hierarchy(
    entity_id: str,
    linearization: Optional[str] = "mms",
    language: Optional[str] = "en",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Navigate the ICD-11 disease classification hierarchy by retrieving child entities of a parent cat...

    Parameters
    ----------
    entity_id : str
        Parent entity ID to browse (use empty string or root ID for top-level chapters)
    linearization : str
        ICD-11 linearization to browse
    language : str
        Language for results
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
            "name": "ICD11_browse_hierarchy",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ICD11_browse_hierarchy"]
