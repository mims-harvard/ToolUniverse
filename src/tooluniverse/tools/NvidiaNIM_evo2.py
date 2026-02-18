"""
NvidiaNIM_evo2

Generate DNA sequences using Evo2-40B via NVIDIA NIM. 40 billion parameter model trained on 9 tri...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NvidiaNIM_evo2(
    sequence: str,
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
) -> Any:
    """
    Generate DNA sequences using Evo2-40B via NVIDIA NIM. 40 billion parameter model trained on 9 tri...

    Parameters
    ----------
    sequence : str
        Input DNA sequence (A, C, T, G characters only)
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
    Any
    """
    # Handle mutable defaults to avoid B006 linting error

    return get_shared_client().run_one_function(
        {
            "name": "NvidiaNIM_evo2",
            "arguments": {
                "sequence": sequence,
                "num_tokens": num_tokens,
                "temperature": temperature,
                "top_k": top_k,
                "top_p": top_p,
                "enable_sampled_probs": enable_sampled_probs,
                "enable_logits": enable_logits,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NvidiaNIM_evo2"]
