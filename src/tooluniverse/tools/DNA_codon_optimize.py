"""
DNA_codon_optimize

Codon-optimize an amino acid sequence for expression in a target species (human, ecoli, mouse, or...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DNA_codon_optimize(
    operation: str,
    sequence: str,
    species: Optional[str | Any] = "human",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Codon-optimize an amino acid sequence for expression in a target species (human, ecoli, mouse, or...

    Parameters
    ----------
    operation : str
        Operation type
    sequence : str
        Amino acid sequence in single-letter code (e.g., 'MEPVDDLPL'). Stop codon (*)...
    species : str | Any
        Target expression organism. Options: 'human' (default), 'ecoli', 'mouse', 'ye...
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
            "sequence": sequence,
            "species": species,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DNA_codon_optimize",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DNA_codon_optimize"]
