"""
Reactome_map_uniprot_to_pathways

Map a UniProt protein identifier to Reactome pathways. Returns all pathways that contain this pro...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Reactome_map_uniprot_to_pathways(
    uniprot_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Map a UniProt protein identifier to Reactome pathways. Returns all pathways that contain this pro...

    Parameters
    ----------
    uniprot_id : str
        UniProt protein accession (e.g., 'P04637' for TP53, 'P00533' for EGFR)
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"uniprot_id": uniprot_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Reactome_map_uniprot_to_pathways",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Reactome_map_uniprot_to_pathways"]
