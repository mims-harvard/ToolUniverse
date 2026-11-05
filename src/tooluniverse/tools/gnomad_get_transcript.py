"""
gnomad_get_transcript

Get basic transcript metadata from gnomAD by Ensembl transcript ID (e.g., ENST...). The response ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def gnomad_get_transcript(
    transcript_id: str,
    reference_genome: Optional[str] = "GRCh38",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get basic transcript metadata from gnomAD by Ensembl transcript ID (e.g., ENST...). The response ...

    Parameters
    ----------
    transcript_id : str
        Ensembl transcript ID (e.g., 'ENST00000357654').
    reference_genome : str
        Reference genome.
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
        for k, v in {
            "transcript_id": transcript_id,
            "reference_genome": reference_genome,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "gnomad_get_transcript",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["gnomad_get_transcript"]
