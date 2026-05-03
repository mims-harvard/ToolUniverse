"""
gnomad_get_sv_by_region

Get structural variants (SVs) from gnomAD v4 overlapping a genomic region. Returns DEL/DUP/INV/BN...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def gnomad_get_sv_by_region(
    chrom: str,
    start: int,
    stop: int,
    reference_genome: Optional[str] = "GRCh38",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get structural variants (SVs) from gnomAD v4 overlapping a genomic region. Returns DEL/DUP/INV/BN...

    Parameters
    ----------
    chrom : str
        Chromosome (e.g., '17', 'X').
    start : int
        Start position (1-based, GRCh38 by default).
    stop : int
        Stop position.
    reference_genome : str
        Reference genome assembly.
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
            "chrom": chrom,
            "start": start,
            "stop": stop,
            "reference_genome": reference_genome,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "gnomad_get_sv_by_region",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["gnomad_get_sv_by_region"]
