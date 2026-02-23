"""
PubChemTox_get_target_organs

Get the target organs affected by a toxic chemical compound from PubChem. Returns the organs and ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubChemTox_get_target_organs(
    cid: Optional[int | Any] = None,
    compound_name: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the target organs affected by a toxic chemical compound from PubChem. Returns the organs and ...

    Parameters
    ----------
    cid : int | Any
        PubChem Compound ID. Examples: 5359596 (arsenic), 5352425 (lead), 23978 (merc...
    compound_name : str | Any
        Compound name (used if cid is not provided). Examples: 'arsenic', 'lead', 'me...
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

    return get_shared_client().run_one_function(
        {
            "name": "PubChemTox_get_target_organs",
            "arguments": {"cid": cid, "compound_name": compound_name},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubChemTox_get_target_organs"]
