"""
CodonUsage_get_optimal_codons

Return the most-used codon for each amino acid in an organism, which is the reference table neede...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CodonUsage_get_optimal_codons(
    taxid: int | str,
    include_stop_codons: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Return the most-used codon for each amino acid in an organism, which is the reference table neede...

    Parameters
    ----------
    taxid : int | str
        NCBI taxonomy identifier, e.g. 9606 (human) or 83333 (E. coli K-12).
    include_stop_codons : bool
        Include the stop codon group (reported as 'End'). Default false.
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
        for k, v in {"taxid": taxid, "include_stop_codons": include_stop_codons}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CodonUsage_get_optimal_codons",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CodonUsage_get_optimal_codons"]
