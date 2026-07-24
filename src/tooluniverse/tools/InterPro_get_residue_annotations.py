"""
InterPro_get_residue_annotations

Get InterPro residue-level functional site annotations for a protein by UniProt accession. Return...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def InterPro_get_residue_annotations(
    protein_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get InterPro residue-level functional site annotations for a protein by UniProt accession. Return...

    Parameters
    ----------
    protein_id : str
        UniProt accession (e.g., 'P00533' EGFR, 'P04637' TP53, 'P00519' ABL1)
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
            "name": "InterPro_get_residue_annotations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["InterPro_get_residue_annotations"]
