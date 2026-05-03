"""
Reactome_get_participant_reference_entities

Get reference entities for participants of a reaction or event. Returns list of reference entitie...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Reactome_get_participant_reference_entities(
    stId: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get reference entities for participants of a reaction or event. Returns list of reference entitie...

    Parameters
    ----------
    stId : str
        Event Stable ID (reaction or pathway, e.g., 'R-HSA-111289'). To find reaction...
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
    _args = {k: v for k, v in {"stId": stId}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Reactome_get_participant_reference_entities",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Reactome_get_participant_reference_entities"]
