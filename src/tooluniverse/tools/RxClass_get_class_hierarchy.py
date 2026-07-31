"""
RxClass_get_class_hierarchy

Traverse the drug-class hierarchy (ancestor chain / class tree) for a class ID in NLM RxClass via...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RxClass_get_class_hierarchy(
    class_id: str,
    source: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Traverse the drug-class hierarchy (ancestor chain / class tree) for a class ID in NLM RxClass via...

    Parameters
    ----------
    class_id : str
        Drug class identifier whose ancestor chain to traverse. ATC class codes: 'N02...
    source : str
        Optional classification source/vocabulary for the graph. Default: ATC (the AP...
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
        k: v
        for k, v in {"class_id": class_id, "source": source}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RxClass_get_class_hierarchy",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RxClass_get_class_hierarchy"]
