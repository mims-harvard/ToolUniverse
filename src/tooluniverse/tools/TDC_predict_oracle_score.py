"""
TDC_predict_oracle_score

Score one or more molecules (SMILES) with a pretrained Therapeutics Data Commons (TDC) oracle, co...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TDC_predict_oracle_score(
    smiles: str | list[str],
    oracle: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Score one or more molecules (SMILES) with a pretrained Therapeutics Data Commons (TDC) oracle, co...

    Parameters
    ----------
    smiles : str | list[str]
        A single SMILES string or a list of SMILES strings to score. Example: 'CC(=O)...
    oracle : str
        Oracle name (case-insensitive). One of: QED, SA, LogP, GSK3B, JNK3, DRD2.
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
        k: v for k, v in {"smiles": smiles, "oracle": oracle}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "TDC_predict_oracle_score",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TDC_predict_oracle_score"]
