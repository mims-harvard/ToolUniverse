"""
SwissTargetPrediction_predict

Predict the most probable protein targets of a small molecule using SwissTargetPrediction. Given ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SwissTargetPrediction_predict(
    operation: str,
    smiles: str,
    organism: Optional[str | Any] = "Homo_sapiens",
    top_n: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Predict the most probable protein targets of a small molecule using SwissTargetPrediction. Given ...

    Parameters
    ----------
    operation : str
        Operation type
    smiles : str
        SMILES representation of the query molecule. Must be a valid, druglike small ...
    organism : str | Any
        Target organism proteome. Use underscores. Valid options: Homo_sapiens (defau...
    top_n : int | Any
        Return only the top N predictions ranked by probability. If null, returns all...
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
            "smiles": smiles,
            "organism": organism,
            "top_n": top_n,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SwissTargetPrediction_predict",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SwissTargetPrediction_predict"]
