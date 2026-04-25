"""
ClinGen_dosage_region_search

Search ClinGen dosage sensitivity curations by genomic region. Returns all genes and recurrent CN...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinGen_dosage_region_search(
    chromosome: str,
    start: int,
    end: int,
    assembly: Optional[str] = 'GRCh38',
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search ClinGen dosage sensitivity curations by genomic region. Returns all genes and recurrent CN...

    Parameters
    ----------
    chromosome : str
        Chromosome (e.g., '17', 'X').
    start : int
        Start position.
    end : int
        End position.
    assembly : str
        Genome assembly version.
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
    _args = {k: v for k, v in {
        "chromosome": chromosome,
                "start": start,
                "end": end,
                "assembly": assembly
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ClinGen_dosage_region_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["ClinGen_dosage_region_search"]
