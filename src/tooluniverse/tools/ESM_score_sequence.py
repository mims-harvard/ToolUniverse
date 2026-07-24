"""
ESM_score_sequence

Score a protein sequence using ESMC logits to compute per-residue log-probabilities and mean pseu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ESM_score_sequence(
    sequence: str,
    model: Optional[str] = "esmc-300m-2024-12",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Score a protein sequence using ESMC logits to compute per-residue log-probabilities and mean pseu...

    Parameters
    ----------
    sequence : str
        Protein amino acid sequence in single-letter code to score (e.g. 'MKTAYIAKQRQ...
    model : str
        ESMC model to use for scoring.
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
        k: v for k, v in {"sequence": sequence, "model": model}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ESM_score_sequence",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ESM_score_sequence"]
