"""
PubChemTox_get_carcinogen_classification

Get carcinogen classification data for a chemical compound from PubChem. Returns classifications ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubChemTox_get_carcinogen_classification(
    cid: Optional[int | Any] = None,
    compound_name: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get carcinogen classification data for a chemical compound from PubChem. Returns classifications ...

    Parameters
    ----------
    cid : int | Any
        PubChem Compound ID. Examples: 5359596 (arsenic), 241 (benzene), 24524 (forma...
    compound_name : str | Any
        Compound name (used if cid is not provided). Examples: 'arsenic', 'benzene', ...
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
            "name": "PubChemTox_get_carcinogen_classification",
            "arguments": {"cid": cid, "compound_name": compound_name},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubChemTox_get_carcinogen_classification"]
