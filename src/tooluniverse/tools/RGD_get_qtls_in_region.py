"""
RGD_get_qtls_in_region

Get QTLs (Quantitative Trait Loci) overlapping a genomic region from the Rat Genome Database (RGD...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RGD_get_qtls_in_region(
    chromosome: str,
    start: int,
    stop: int,
    map_key: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get QTLs (Quantitative Trait Loci) overlapping a genomic region from the Rat Genome Database (RGD...

    Parameters
    ----------
    chromosome : str
        Chromosome name, e.g. '10' or 'chr10'.
    start : int
        Region start coordinate (1-based).
    stop : int
        Region stop coordinate.
    map_key : int
        Assembly map key. 360=rat rn7/GRCr8, 372=rat mRatBN7.2, 38=human GRCh38, 17=h...
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
            "chromosome": chromosome,
            "start": start,
            "stop": stop,
            "map_key": map_key,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RGD_get_qtls_in_region",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RGD_get_qtls_in_region"]
