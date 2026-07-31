"""
Pathoplexus_get_mutations

Get characteristic amino-acid (default) or nucleotide mutations for a Pathoplexus organism above ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Pathoplexus_get_mutations(
    organism: str,
    country: Optional[str] = None,
    lineage: Optional[str] = None,
    min_proportion: Optional[float] = None,
    mutation_type: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get characteristic amino-acid (default) or nucleotide mutations for a Pathoplexus organism above ...

    Parameters
    ----------
    organism : str
        Pathoplexus organism slug, e.g. 'west-nile', 'mpox'.
    country : str
        Filter by country (geoLocCountry).
    lineage : str
        Filter by lineage.
    min_proportion : float
        Minimum proportion of sequences carrying the mutation (default 0.8).
    mutation_type : str
        'aminoAcid' (default) or 'nucleotide'.
    limit : int
        Max mutations (default 50, max 500).
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
            "organism": organism,
            "country": country,
            "lineage": lineage,
            "min_proportion": min_proportion,
            "mutation_type": mutation_type,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Pathoplexus_get_mutations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Pathoplexus_get_mutations"]
