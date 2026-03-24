"""
RxClass_get_class_members

List all drugs belonging to a specific drug class by class ID in NLM RxClass.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RxClass_get_class_members(
    class_id: str,
    rela_source: Optional[str] = None,
    ttys: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List all drugs belonging to a specific drug class.

    Parameters
    ----------
    class_id : str
        Drug class identifier (e.g., 'M01AE' for propionic acid derivatives).
    rela_source : str, optional
        Classification source: 'ATC' (default), 'FDASPL', 'MESH', 'VA', 'DAILYMED'.
    ttys : str, optional
        RxNorm term types: 'IN' (ingredients, default), 'PIN', 'MIN', 'SCD'.
    limit : int, optional
        Maximum number of drugs to return (default 50).
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
    _args = {
        k: v
        for k, v in {
            "class_id": class_id,
            "rela_source": rela_source,
            "ttys": ttys,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RxClass_get_class_members",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RxClass_get_class_members"]
