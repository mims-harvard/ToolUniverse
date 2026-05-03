"""
APPRIS_get_isoforms

Get all transcript isoforms and their APPRIS annotations for a gene. APPRIS classifies isoforms a...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def APPRIS_get_isoforms(
    gene_id: str,
    species: Optional[str] = "homo_sapiens",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get all transcript isoforms and their APPRIS annotations for a gene. APPRIS classifies isoforms a...

    Parameters
    ----------
    gene_id : str
        Ensembl gene ID (e.g., ENSG00000141510 for TP53, ENSG00000012048 for BRCA1).
    species : str
        Species name in lowercase with underscore (e.g., homo_sapiens, mus_musculus, ...
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
    _args = {
        k: v
        for k, v in {"gene_id": gene_id, "species": species}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "APPRIS_get_isoforms",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["APPRIS_get_isoforms"]
