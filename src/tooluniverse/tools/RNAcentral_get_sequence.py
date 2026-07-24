"""
RNAcentral_get_sequence

Get the nucleotide sequence (FASTA) of a non-coding RNA from RNAcentral. Provide an RNAcentral UR...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RNAcentral_get_sequence(
    urs_id: str,
    operation: Optional[str] = "sequence",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the nucleotide sequence (FASTA) of a non-coding RNA from RNAcentral. Provide an RNAcentral UR...

    Parameters
    ----------
    operation : str
        Fixed to 'sequence' for this tool.
    urs_id : str
        RNAcentral URS identifier, e.g. 'URS00003B7674'. A trailing '_taxid' suffix i...
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
        for k, v in {"operation": operation, "urs_id": urs_id}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RNAcentral_get_sequence",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RNAcentral_get_sequence"]
