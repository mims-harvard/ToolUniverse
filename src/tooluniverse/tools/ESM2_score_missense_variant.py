"""
ESM2_score_missense_variant

Score a missense protein variant with ESM-2 masked-marginal log-likelihood ratio (Meier 2021) ove...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ESM2_score_missense_variant(
    sequence: str,
    position: int,
    mutant: str,
    wild_type: Optional[str] = None,
    model_id: Optional[str] = None,
    wait_for_model: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Score a missense protein variant with ESM-2 masked-marginal log-likelihood ratio (Meier 2021) ove...

    Parameters
    ----------
    sequence : str
        Wild-type protein sequence in 1-letter amino-acid code (whitespace is ignored).
    position : int
        1-based residue position of the variant within the sequence.
    mutant : str
        Mutant amino acid (single 1-letter code, one of the 20 standard residues).
    wild_type : str
        Optional wild-type residue (1-letter). If given, it is validated against the ...
    model_id : str
        ESM-2 model to use. Default 'facebook/esm2_t33_650M_UR50D'. Other sizes: esm2...
    wait_for_model : bool
        If true, block until the model finishes loading on the HF servers instead of ...
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
            "sequence": sequence,
            "position": position,
            "mutant": mutant,
            "wild_type": wild_type,
            "model_id": model_id,
            "wait_for_model": wait_for_model,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ESM2_score_missense_variant",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ESM2_score_missense_variant"]
