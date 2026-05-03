"""
ADMETAI_predict_CYP_interactions

Predicts CYP enzyme interactions for a given list of molecules in SMILES format.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ADMETAI_predict_CYP_interactions(
    smiles: list[str] | str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Predicts CYP enzyme interactions for a given list of molecules in SMILES format.

    Parameters
    ----------
    smiles : list[str] | str
        SMILES string(s) for the molecule(s). Accepts a single string or list of stri...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"smiles": smiles}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ADMETAI_predict_CYP_interactions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ADMETAI_predict_CYP_interactions"]
