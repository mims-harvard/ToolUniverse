"""
IUPred3_predict_disorder

Predict intrinsically disordered protein regions from sequence using the IUPred3 algorithm. Input...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IUPred3_predict_disorder(
    accession: str,
    iupred_type: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Predict intrinsically disordered protein regions from sequence using the IUPred3 algorithm. Input...

    Parameters
    ----------
    accession : str
        UniProt accession or entry ID, e.g. 'P04637' (human p53) or 'TP53_HUMAN'. The...
    iupred_type : str
        Prediction mode. 'long' (default) = long disordered regions; 'short' = short ...
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
    _args = {
        k: v
        for k, v in {"accession": accession, "iupred_type": iupred_type}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "IUPred3_predict_disorder",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IUPred3_predict_disorder"]
