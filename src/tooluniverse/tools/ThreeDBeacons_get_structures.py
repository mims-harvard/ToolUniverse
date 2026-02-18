"""
ThreeDBeacons_get_structures

Get detailed list of 3D structure models for a protein from the 3D Beacons Hub. Returns individua...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ThreeDBeacons_get_structures(
    accession: str,
    category: Optional[str] = None,
    provider: Optional[str] = None,
    max_results: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed list of 3D structure models for a protein from the 3D Beacons Hub. Returns individua...

    Parameters
    ----------
    accession : str
        UniProt protein accession. Examples: 'P04637' (TP53), 'P00533' (EGFR), 'P0130...
    category : str
        Filter by model category. Options: 'EXPERIMENTALLY DETERMINED', 'TEMPLATE-BAS...
    provider : str
        Filter by data provider. Options: 'PDBe', 'AlphaFold DB', 'SWISS-MODEL', 'PED...
    max_results : int
        Maximum structures to return (default 20, max 100).
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
            "name": "ThreeDBeacons_get_structures",
            "arguments": {
                "accession": accession,
                "category": category,
                "provider": provider,
                "max_results": max_results,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ThreeDBeacons_get_structures"]
