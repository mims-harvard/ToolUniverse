"""
ClinGen_get_variant_classifications

Get variant pathogenicity classifications from ClinGen Evidence Repository. Returns expert-curate...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinGen_get_variant_classifications(
    gene: Optional[str] = None,
    variant: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get variant pathogenicity classifications from ClinGen Evidence Repository. Returns expert-curate...

    Parameters
    ----------
    gene : str
        Optional: Filter by gene symbol
    variant : str
        Optional: Filter by variant (HGVS notation or protein change)
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
            "name": "ClinGen_get_variant_classifications",
            "arguments": {"gene": gene, "variant": variant},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinGen_get_variant_classifications"]
