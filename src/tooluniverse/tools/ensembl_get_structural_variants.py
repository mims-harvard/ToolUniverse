"""
ensembl_get_structural_variants

Get structural variants overlapping a genomic region from Ensembl. Returns known SVs from DGVa (D...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ensembl_get_structural_variants(
    species: str,
    region: str,
    feature: Optional[str] = "structural_variation",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get structural variants overlapping a genomic region from Ensembl. Returns known SVs from DGVa (D...

    Parameters
    ----------
    species : str
        Species name (e.g., 'human', 'homo_sapiens').
    region : str
        Genomic region in format 'chr:start-end' (e.g., '17:43044295-43125370'). Maxi...
    feature : str
        Feature type to retrieve. Fixed to 'structural_variation' for this tool.
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
        for k, v in {"species": species, "region": region, "feature": feature}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ensembl_get_structural_variants",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ensembl_get_structural_variants"]
