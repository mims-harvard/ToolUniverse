"""
OMA_get_protein

Get protein information from the OMA (Orthologous MAtrix) Browser by UniProt accession or OMA ID....
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OMA_get_protein(
    protein_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get protein information from the OMA (Orthologous MAtrix) Browser by UniProt accession or OMA ID....

    Parameters
    ----------
    protein_id : str
        UniProt accession (e.g., 'P04637' for human p53) or OMA ID (e.g., 'HUMAN31534...
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
    _args = {k: v for k, v in {"protein_id": protein_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OMA_get_protein",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OMA_get_protein"]
