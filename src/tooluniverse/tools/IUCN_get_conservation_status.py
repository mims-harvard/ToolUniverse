"""
IUCN_get_conservation_status

Get the IUCN Red List conservation (extinction-risk) status for a species by scientific name. Ret...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IUCN_get_conservation_status(
    scientific_name: Optional[str] = None,
    genus_name: Optional[str] = None,
    species_name: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the IUCN Red List conservation (extinction-risk) status for a species by scientific name. Ret...

    Parameters
    ----------
    scientific_name : str
        Binomial 'Genus species', e.g. 'Panthera leo', 'Loxodonta africana'.
    genus_name : str
        Genus (alternative to scientific_name), e.g. 'Panthera'.
    species_name : str
        Species epithet (alternative to scientific_name), e.g. 'leo'.
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
            "scientific_name": scientific_name,
            "genus_name": genus_name,
            "species_name": species_name,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "IUCN_get_conservation_status",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IUCN_get_conservation_status"]
