"""
DNA_translate_sequence

Translate a DNA coding sequence to protein using the standard genetic code (NCBI Code 1). Returns...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DNA_translate_sequence(
    operation: str,
    sequence: str,
    codon_table: Optional[str | Any] = "standard",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Translate a DNA coding sequence to protein using the standard genetic code (NCBI Code 1). Returns...

    Parameters
    ----------
    operation : str
        Operation type
    sequence : str
        DNA coding sequence starting with ATG (A, T, G, C only). Should be in-frame.
    codon_table : str | Any
        Genetic code to use. Currently only 'standard' (NCBI Code 1) is supported.
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
            "operation": operation,
            "sequence": sequence,
            "codon_table": codon_table,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DNA_translate_sequence",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DNA_translate_sequence"]
