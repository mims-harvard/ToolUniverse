"""
ensembl_get_variation

Get detailed information about a specific genetic variation by its ID (e.g., rs699). Returns vari...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ensembl_get_variation(
    id: Optional[str] = None,
    variant_id: Optional[str] = None,
    species: Optional[str] = "human",
    phenotypes: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information about a specific genetic variation by its ID (e.g., rs699). Returns vari...

    Parameters
    ----------
    id : str
        Variation ID (e.g., 'rs699', 'rs1421085'). Use ensembl_get_variants to find v...
    variant_id : str
        Alias for id. dbSNP rsID or Ensembl variation ID (e.g., 'rs7903146', 'rs699').
    species : str
        Species name (default 'human')
    phenotypes : int
        Include phenotype associations (0=no, 1=yes)
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
            "id": id,
            "variant_id": variant_id,
            "species": species,
            "phenotypes": phenotypes,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ensembl_get_variation",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ensembl_get_variation"]
