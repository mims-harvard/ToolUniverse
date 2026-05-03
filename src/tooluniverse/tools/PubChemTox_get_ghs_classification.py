"""
PubChemTox_get_ghs_classification

Get GHS (Globally Harmonized System) hazard classification for a chemical compound from PubChem. ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubChemTox_get_ghs_classification(
    cid: Optional[int | Any] = None,
    compound_name: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get GHS (Globally Harmonized System) hazard classification for a chemical compound from PubChem. ...

    Parameters
    ----------
    cid : int | Any
        PubChem Compound ID. Examples: 5359596 (arsenic), 2244 (aspirin), 702 (ethano...
    compound_name : str | Any
        Compound name (used if cid is not provided). Examples: 'arsenic', 'aspirin', ...
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
        for k, v in {"cid": cid, "compound_name": compound_name}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PubChemTox_get_ghs_classification",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubChemTox_get_ghs_classification"]
