"""
SwissADME_check_druglikeness

Quick drug-likeness assessment of a small molecule using SwissADME. Evaluates the molecule agains...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SwissADME_check_druglikeness(
    operation: str,
    smiles: str,
    rules: Optional[list[str] | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Quick drug-likeness assessment of a small molecule using SwissADME. Evaluates the molecule agains...

    Parameters
    ----------
    operation : str
        Operation type
    smiles : str
        SMILES string of the molecule to check. Must be a valid small molecule SMILES.
    rules : list[str] | Any
        Optional list of specific drug-likeness rules to check. If null, all 5 rules ...
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
    _args = {k: v for k, v in {
        "operation": operation,
                "smiles": smiles,
                "rules": rules
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "SwissADME_check_druglikeness",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["SwissADME_check_druglikeness"]
