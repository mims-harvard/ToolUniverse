"""
Pfam_get_protein_annotations

Get all Pfam domain annotations for a specific protein by its UniProt accession. Returns every Pf...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Pfam_get_protein_annotations(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get all Pfam domain annotations for a specific protein by its UniProt accession. Returns every Pf...

    Parameters
    ----------
    accession : str
        UniProt protein accession. Examples: 'P04637' (TP53, 4 domains), 'P00533' (EG...
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
    _args = {k: v for k, v in {
        "accession": accession
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Pfam_get_protein_annotations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["Pfam_get_protein_annotations"]
