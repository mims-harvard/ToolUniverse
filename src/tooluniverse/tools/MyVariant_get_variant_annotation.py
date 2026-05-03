"""
MyVariant_get_variant_annotation

Get detailed annotations for a specific variant by its HGVS ID (e.g., 'chr1:g.2186318G>A'). Retur...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MyVariant_get_variant_annotation(
    variant_id: str,
    fields: Optional[str] = "dbsnp,clinvar,cadd,gnomad_genome,dbnsfp",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed annotations for a specific variant by its HGVS ID (e.g., 'chr1:g.2186318G>A'). Retur...

    Parameters
    ----------
    variant_id : str
        HGVS variant ID (e.g., 'chr1:g.2186318G>A' or 'rs123').
    fields : str
        Fields to return. Useful fields: dbsnp, clinvar, cadd, gnomad_genome, gnomad_...
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
        for k, v in {"variant_id": variant_id, "fields": fields}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MyVariant_get_variant_annotation",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MyVariant_get_variant_annotation"]
