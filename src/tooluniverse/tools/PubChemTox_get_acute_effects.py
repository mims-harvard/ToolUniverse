"""
PubChemTox_get_acute_effects

Get acute toxicity effects for a chemical compound from PubChem. Returns documented acute (short-...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubChemTox_get_acute_effects(
    cid: Optional[int | Any] = None,
    compound_name: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get acute toxicity effects for a chemical compound from PubChem. Returns documented acute (short-...

    Parameters
    ----------
    cid : int | Any
        PubChem Compound ID. Examples: 5359596 (arsenic), 887 (methanol), 702 (ethano...
    compound_name : str | Any
        Compound name (used if cid is not provided). Examples: 'arsenic', 'methanol',...
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
            "name": "PubChemTox_get_acute_effects",
            "arguments": {"cid": cid, "compound_name": compound_name},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubChemTox_get_acute_effects"]
