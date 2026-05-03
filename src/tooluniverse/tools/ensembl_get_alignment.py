"""
ensembl_get_alignment

Get genomic alignments between species for a genomic region. Returns multiple alignments showing ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ensembl_get_alignment(
    species: str,
    region: str,
    species_set_group: Optional[str] = "mammals",
    method: Optional[str] = "EPO",
    compact: Optional[bool] = True,
    display_species_set: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get genomic alignments between species for a genomic region. Returns multiple alignments showing ...

    Parameters
    ----------
    species : str
        Source species (e.g., 'human', 'homo_sapiens')
    region : str
        Genomic region in format 'chromosome:start-end' (e.g., '2:106000000-106100000')
    species_set_group : str
        Predefined species group for multiple alignment. Options: 'mammals', 'primate...
    method : str
        Alignment method: EPO (high quality multiple), EPO_EXTENDED (extended coverag...
    compact : bool
        Compact output format
    display_species_set : str
        Comma-separated list to filter which species to display in results (optional,...
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
        for k, v in {
            "species": species,
            "region": region,
            "species_set_group": species_set_group,
            "method": method,
            "compact": compact,
            "display_species_set": display_species_set,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ensembl_get_alignment",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ensembl_get_alignment"]
