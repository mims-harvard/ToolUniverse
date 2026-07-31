"""
OMA_get_protein_go

Get Gene Ontology (GO) functional annotations for a specific OMA protein. OMA attaches per-entry ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OMA_get_protein_go(
    protein_id: str,
    aspect: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get Gene Ontology (GO) functional annotations for a specific OMA protein. OMA attaches per-entry ...

    Parameters
    ----------
    protein_id : str
        OMA ID (e.g. 'HUMAN17018') or UniProt accession (e.g. 'P04637').
    aspect : str
        Optional GO aspect filter: 'biological_process', 'molecular_function', or 'ce...
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
        for k, v in {"protein_id": protein_id, "aspect": aspect}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OMA_get_protein_go",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OMA_get_protein_go"]
