"""
AlphaMissense_get_protein_scores

Get all AlphaMissense pathogenicity scores for a protein by UniProt ID. Returns comprehensive res...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def AlphaMissense_get_protein_scores(
    uniprot_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get all AlphaMissense pathogenicity scores for a protein by UniProt ID. Returns comprehensive res...

    Parameters
    ----------
    uniprot_id : str
        UniProt accession ID (e.g., 'P00533' for EGFR)
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
    _args = {k: v for k, v in {"uniprot_id": uniprot_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "AlphaMissense_get_protein_scores",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["AlphaMissense_get_protein_scores"]
