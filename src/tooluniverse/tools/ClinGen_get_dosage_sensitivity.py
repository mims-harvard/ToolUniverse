"""
ClinGen_get_dosage_sensitivity

Get all ClinGen dosage sensitivity curations. Returns haploinsufficiency and triplosensitivity sc...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinGen_get_dosage_sensitivity(
    gene: Optional[str] = None,
    include_regions: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get all ClinGen dosage sensitivity curations. Returns haploinsufficiency and triplosensitivity sc...

    Parameters
    ----------
    gene : str
        Optional: Filter by gene symbol
    include_regions : bool
        Include recurrent CNV regions (default: false)
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

    return get_shared_client().run_one_function(
        {
            "name": "ClinGen_get_dosage_sensitivity",
            "arguments": {"gene": gene, "include_regions": include_regions},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinGen_get_dosage_sensitivity"]
