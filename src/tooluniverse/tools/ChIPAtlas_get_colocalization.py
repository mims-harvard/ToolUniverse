"""
ChIPAtlas_get_colocalization

ChIP-Atlas Colocalization: for a given antigen/transcription factor in a specific tissue class, r...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChIPAtlas_get_colocalization(
    antigen: str,
    cell_type_class: str,
    operation: Optional[str] = "get_colocalization",
    genome: Optional[str] = "hg38",
    limit: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    ChIP-Atlas Colocalization: for a given antigen/transcription factor in a specific tissue class, r...

    Parameters
    ----------
    operation : str

    antigen : str
        Antigen / transcription factor symbol (e.g. 'CTCF', 'AFF4').
    cell_type_class : str
        Tissue / cell-type class for which the colocalization matrix was computed (e....
    genome : str
        Genome assembly.
    limit : int
        Maximum number of ranked partner proteins to return.
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
        for k, v in {
            "operation": operation,
            "antigen": antigen,
            "cell_type_class": cell_type_class,
            "genome": genome,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChIPAtlas_get_colocalization",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChIPAtlas_get_colocalization"]
