"""
RXNChemistry_predict_retrosynthesis

Predict retrosynthetic routes for a target molecule using IBM RXN for Chemistry (ML retrosynthesi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RXNChemistry_predict_retrosynthesis(
    product: str,
    operation: Optional[str] = None,
    ai_model: Optional[str] = None,
    max_steps: Optional[int] = None,
    project_id: Optional[str] = None,
    poll_interval: Optional[float] = None,
    max_wait_time: Optional[float] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Predict retrosynthetic routes for a target molecule using IBM RXN for Chemistry (ML retrosynthesi...

    Parameters
    ----------
    operation : str
        Operation type (fixed: predict_retrosynthesis).
    product : str
        Target product SMILES to retrosynthesize. Example: 'CC(=O)Oc1ccccc1C(=O)O' (a...
    ai_model : str
        Optional IBM RXN retrosynthesis model id. Defaults to '2020-08-10'.
    max_steps : int
        Optional maximum number of retrosynthetic steps to explore.
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
            "product": product,
            "ai_model": ai_model,
            "max_steps": max_steps,
            "project_id": project_id,
            "poll_interval": poll_interval,
            "max_wait_time": max_wait_time,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RXNChemistry_predict_retrosynthesis",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RXNChemistry_predict_retrosynthesis"]
