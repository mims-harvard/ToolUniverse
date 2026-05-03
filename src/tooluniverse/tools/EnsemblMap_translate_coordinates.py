"""
EnsemblMap_translate_coordinates

Map protein or cDNA positions to genomic coordinates using Ensembl. Converts positions from trans...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EnsemblMap_translate_coordinates(
    ensembl_id: str,
    start: int,
    end: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Map protein or cDNA positions to genomic coordinates using Ensembl. Converts positions from trans...

    Parameters
    ----------
    ensembl_id : str
        Ensembl transcript ID (ENST*) for cDNA mapping, or Ensembl protein ID (ENSP*)...
    start : int
        Start position in transcript/protein coordinates (1-based). For cDNA: nucleot...
    end : int
        End position in transcript/protein coordinates (1-based).
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
        for k, v in {"ensembl_id": ensembl_id, "start": start, "end": end}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EnsemblMap_translate_coordinates",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EnsemblMap_translate_coordinates"]
