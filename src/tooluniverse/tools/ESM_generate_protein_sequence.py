"""
ESM_generate_protein_sequence

Generate or complete a protein sequence using ESM3, EvolutionaryScale's generative protein langua...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ESM_generate_protein_sequence(
    prompt_sequence: str,
    model: Optional[str] = "esm3-open-2024-03",
    num_steps: Optional[int] = 8,
    temperature: Optional[float] = 1.0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Generate or complete a protein sequence using ESM3, EvolutionaryScale's generative protein langua...

    Parameters
    ----------
    prompt_sequence : str
        Protein sequence template with '_' at positions to generate. Use standard ami...
    model : str
        ESM3 model to use for generation.
    num_steps : int
        Number of iterative decoding steps (default: 8). More steps = slower but pote...
    temperature : float
        Sampling temperature (default: 1.0). Lower values (0.1-0.5) produce more cons...
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
            "prompt_sequence": prompt_sequence,
            "model": model,
            "num_steps": num_steps,
            "temperature": temperature,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ESM_generate_protein_sequence",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ESM_generate_protein_sequence"]
