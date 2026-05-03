"""
ProtVar_get_function

Get functional annotations at a specific amino acid position from ProtVar. Returns annotated UniP...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ProtVar_get_function(
    accession: str,
    position: int,
    variant_aa: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get functional annotations at a specific amino acid position from ProtVar. Returns annotated UniP...

    Parameters
    ----------
    accession : str
        UniProt accession (e.g. 'P04637' for TP53).
    position : int
        Amino acid position in the protein (1-based).
    variant_aa : str
        Single-letter code for the variant amino acid (e.g. 'H' for histidine). Optio...
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
            "accession": accession,
            "position": position,
            "variant_aa": variant_aa,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ProtVar_get_function",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ProtVar_get_function"]
