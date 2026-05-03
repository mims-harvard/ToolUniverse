"""
NCI_expand_drugs_by_letter

Browse the NCI Drug Dictionary by first letter. Returns all cancer drugs and drug aliases startin...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCI_expand_drugs_by_letter(
    letter: str,
    size: Optional[int] = 100,
    from_: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Browse the NCI Drug Dictionary by first letter. Returns all cancer drugs and drug aliases startin...

    Parameters
    ----------
    letter : str
        First letter to browse by (a-z, or '#' for drugs starting with numbers/specia...
    size : int
        Number of results per page (default: 100, max: 10000)
    from_ : int
        Offset for pagination (default: 0)
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
        for k, v in {"letter": letter, "size": size, "from": from_}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NCI_expand_drugs_by_letter",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCI_expand_drugs_by_letter"]
