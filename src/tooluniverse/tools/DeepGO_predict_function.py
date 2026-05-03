"""
DeepGO_predict_function

Predict protein function from amino acid sequence using deep learning. Returns Gene Ontology (GO)...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DeepGO_predict_function(
    sequence: str,
    name: Optional[str] = "query",
    threshold: Optional[float] = 0.3,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Predict protein function from amino acid sequence using deep learning. Returns Gene Ontology (GO)...

    Parameters
    ----------
    sequence : str
        Protein sequence (10-5000 amino acids, standard 20 AAs)
    name : str
        Optional name for the protein
    threshold : float
        Confidence threshold 0.1-1.0 (default: 0.3)
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
        for k, v in {"sequence": sequence, "name": name, "threshold": threshold}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DeepGO_predict_function",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DeepGO_predict_function"]
