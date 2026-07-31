"""
RXNChemistry_predict_reaction

Predict the most likely product of a chemical reaction using IBM RXN for Chemistry (ML forward re...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RXNChemistry_predict_reaction(
    reactants: str,
    operation: Optional[str] = None,
    ai_model: Optional[str] = None,
    project_id: Optional[str] = None,
    poll_interval: Optional[float] = None,
    max_wait_time: Optional[float] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Predict the most likely product of a chemical reaction using IBM RXN for Chemistry (ML forward re...

    Parameters
    ----------
    operation : str
        Operation type (fixed: predict_reaction).
    reactants : str
        Reactant and reagent SMILES joined by '.' (dot-separated). Example: 'BrBr.c1c...
    ai_model : str
        Optional IBM RXN AI model id for forward prediction. Defaults to '2020-08-10'.
    project_id : str
        Optional IBM RXN project id to run the prediction under. If omitted, the firs...
    poll_interval : float
        Optional seconds between status polls (default 5).
    max_wait_time : float
        Optional total polling budget in seconds (default 60).
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
        for k, v in {
            "operation": operation,
            "reactants": reactants,
            "ai_model": ai_model,
            "project_id": project_id,
            "poll_interval": poll_interval,
            "max_wait_time": max_wait_time,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RXNChemistry_predict_reaction",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RXNChemistry_predict_reaction"]
