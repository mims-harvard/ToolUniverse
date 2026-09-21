"""
BioThings_get_entity

Retrieve one record from a BioThings API by its _id, as returned in BioThings_query results. Exam...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioThings_get_entity(
    api: str,
    entity_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve one record from a BioThings API by its _id, as returned in BioThings_query results. Exam...

    Parameters
    ----------
    api : str
        API slug, e.g. 'mondo'. See BioThings_list_apis.
    entity_id : str
        Record _id from a BioThings_query result, e.g. 'MONDO:0010329'.
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
        k: v for k, v in {"api": api, "entity_id": entity_id}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BioThings_get_entity",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioThings_get_entity"]
