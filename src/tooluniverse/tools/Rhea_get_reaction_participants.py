"""
Rhea_get_reaction_participants

Return just the structured ChEBI participants (reactants and products) of a single Rhea biochemic...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Rhea_get_reaction_participants(
    rhea_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Return just the structured ChEBI participants (reactants and products) of a single Rhea biochemic...

    Parameters
    ----------
    rhea_id : str
        Rhea reaction identifier, numeric or RHEA-prefixed. Examples: '16505' (choris...
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
    _args = {k: v for k, v in {"rhea_id": rhea_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Rhea_get_reaction_participants",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Rhea_get_reaction_participants"]
