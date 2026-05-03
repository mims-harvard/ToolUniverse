"""
ensembl_get_variation_phenotypes

Get phenotype associations for a specific genetic variation. Returns detailed phenotype informati...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ensembl_get_variation_phenotypes(
    id: str,
    species: Optional[str] = "human",
    phenotypes: Optional[int] = 1,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get phenotype associations for a specific genetic variation. Returns detailed phenotype informati...

    Parameters
    ----------
    id : str
        Variation ID (e.g., 'rs699'). Use ensembl_get_variants to find variant IDs in...
    species : str
        Species name (default 'human')
    phenotypes : int
        Include phenotype associations (must be 1 for this tool)
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
        for k, v in {"id": id, "species": species, "phenotypes": phenotypes}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ensembl_get_variation_phenotypes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ensembl_get_variation_phenotypes"]
