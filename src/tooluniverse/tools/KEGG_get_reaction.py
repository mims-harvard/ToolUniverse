"""
KEGG_get_reaction

Retrieve a KEGG REACTION entry by R-number. Returns the reaction NAME, the human-readable DEFINIT...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def KEGG_get_reaction(
    reaction_id: Optional[str] = None,
    id: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve a KEGG REACTION entry by R-number. Returns the reaction NAME, the human-readable DEFINIT...

    Parameters
    ----------
    reaction_id : str
        KEGG reaction identifier (R-number), e.g. 'R00200' (pyruvate kinase), 'R01786...
    id : str
        Alias for reaction_id.
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
        k: v for k, v in {"reaction_id": reaction_id, "id": id}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "KEGG_get_reaction",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["KEGG_get_reaction"]
