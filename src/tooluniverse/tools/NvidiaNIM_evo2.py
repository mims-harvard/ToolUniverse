"""
NvidiaNIM_evo2

Generate DNA sequences using NVIDIA-hosted Evo 2 (Arc Institute genome foundation model, trained ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NvidiaNIM_evo2(
    sequence: str,
    model: Optional[str] = "evo2-40b",
    num_tokens: Optional[int] = 100,
    temperature: Optional[float] = 0.7,
    top_k: Optional[int] = 1,
    top_p: Optional[float] = None,
    enable_sampled_probs: Optional[bool] = False,
    enable_logits: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Generate DNA sequences using NVIDIA-hosted Evo 2 (Arc Institute genome foundation model, trained ...

    Parameters
    ----------
    sequence : str
        Input DNA sequence (A, C, T, G characters only)
    model : str
        Hosted Evo 2 model size: evo2-40b (default, most accurate) or evo2-7b (smalle...
    num_tokens : int
        Number of nucleotides to generate
    temperature : float
        Sampling temperature
    top_k : int
        Top-k sampling parameter
    top_p : float
        Top-p (nucleus) sampling parameter
    enable_sampled_probs : bool
        Return per-nucleotide probabilities
    enable_logits : bool
        Return raw logits
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
        for k, v in {
            "sequence": sequence,
            "model": model,
            "num_tokens": num_tokens,
            "temperature": temperature,
            "top_k": top_k,
            "top_p": top_p,
            "enable_sampled_probs": enable_sampled_probs,
            "enable_logits": enable_logits,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NvidiaNIM_evo2",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NvidiaNIM_evo2"]
