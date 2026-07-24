"""
Evo2_score_variant

Zero-shot variant-effect scoring with NVIDIA-hosted Evo 2 (Arc Institute genome foundation model)...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Evo2_score_variant(
    ref_sequence: Optional[str] = None,
    alt_sequence: Optional[str] = None,
    sequence: Optional[str] = None,
    position: Optional[int] = None,
    reference: Optional[str] = None,
    alternate: Optional[str] = None,
    model: Optional[str] = "evo2-40b",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Zero-shot variant-effect scoring with NVIDIA-hosted Evo 2 (Arc Institute genome foundation model)...

    Parameters
    ----------
    ref_sequence : str
        Reference DNA window (A/C/G/T/N). Use with alt_sequence (same length).
    alt_sequence : str
        Alternate DNA window, same length/centering as ref_sequence.
    sequence : str
        Reference DNA window for point-substitution mode (use with position + alterna...
    position : int
        1-based position of the substituted base within `sequence`.
    reference : str
        Optional reference base (single letter) at `position`, validated against `seq...
    alternate : str
        Alternate base (single letter) substituted at `position`.
    model : str
        Hosted Evo 2 model size: evo2-40b (default, most accurate) or evo2-7b (smalle...
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
            "ref_sequence": ref_sequence,
            "alt_sequence": alt_sequence,
            "sequence": sequence,
            "position": position,
            "reference": reference,
            "alternate": alternate,
            "model": model,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Evo2_score_variant",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Evo2_score_variant"]
