"""
AlphaMissense_get_residue_scores

Get AlphaMissense scores for all 20 possible amino acid substitutions at a specific protein posit...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def AlphaMissense_get_residue_scores(
    uniprot_id: str,
    position: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get AlphaMissense scores for all 20 possible amino acid substitutions at a specific protein posit...

    Parameters
    ----------
    uniprot_id : str
        UniProt accession ID (e.g., 'P00533' for EGFR)
    position : int
        Amino acid position in the protein (1-indexed)
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
        for k, v in {"uniprot_id": uniprot_id, "position": position}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "AlphaMissense_get_residue_scores",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["AlphaMissense_get_residue_scores"]
