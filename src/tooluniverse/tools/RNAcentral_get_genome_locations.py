"""
RNAcentral_get_genome_locations

Get the genomic coordinates of a non-coding RNA in a specific organism from RNAcentral. Provide a...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RNAcentral_get_genome_locations(
    urs_id: str,
    taxid: int,
    operation: Optional[str] = "genome_locations",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the genomic coordinates of a non-coding RNA in a specific organism from RNAcentral. Provide a...

    Parameters
    ----------
    operation : str
        Fixed to 'genome_locations' for this tool.
    urs_id : str
        RNAcentral URS identifier, e.g. 'URS00003B7674'. A trailing '_taxid' suffix i...
    taxid : int
        NCBI taxonomy id of the organism whose genome mapping is requested, e.g. 9606...
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
        for k, v in {"operation": operation, "urs_id": urs_id, "taxid": taxid}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RNAcentral_get_genome_locations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RNAcentral_get_genome_locations"]
