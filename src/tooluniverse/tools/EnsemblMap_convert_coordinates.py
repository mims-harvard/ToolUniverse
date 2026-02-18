"""
EnsemblMap_convert_coordinates

Convert genomic coordinates between human genome assemblies (e.g., GRCh37/hg19 to GRCh38/hg38 or ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EnsemblMap_convert_coordinates(
    source_assembly: str,
    chromosome: str,
    start: int,
    end: int,
    target_assembly: str,
    species: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Convert genomic coordinates between human genome assemblies (e.g., GRCh37/hg19 to GRCh38/hg38 or ...

    Parameters
    ----------
    species : str
        Species name. Default 'human'. Examples: 'human', 'mouse', 'homo_sapiens', 'm...
    source_assembly : str
        Source genome assembly name. Examples: 'GRCh37', 'GRCh38', 'GRCm38', 'GRCm39'.
    chromosome : str
        Chromosome name (e.g., '1', '17', 'X', 'MT').
    start : int
        Start position on the chromosome (1-based, inclusive).
    end : int
        End position on the chromosome (1-based, inclusive).
    target_assembly : str
        Target genome assembly name. Examples: 'GRCh38', 'GRCh37'.
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

    return get_shared_client().run_one_function(
        {
            "name": "EnsemblMap_convert_coordinates",
            "arguments": {
                "species": species,
                "source_assembly": source_assembly,
                "chromosome": chromosome,
                "start": start,
                "end": end,
                "target_assembly": target_assembly,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EnsemblMap_convert_coordinates"]
