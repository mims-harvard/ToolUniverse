"""
VCF_count_variants

Count variants in a local VCF/BCF after applying filters, via bcftools. Returns total records plu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def VCF_count_variants(
    operation: str,
    vcf_path: str,
    pass_only: Optional[bool] = None,
    regions: Optional[str] = None,
    min_qual: Optional[float] = None,
    include_expr: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Count variants in a local VCF/BCF after applying filters, via bcftools. Returns total records plu...

    Parameters
    ----------
    operation : str
        Operation (fixed)
    vcf_path : str
        Path to a local .vcf, .vcf.gz, or .bcf file
    pass_only : bool
        If true, count only FILTER=PASS or '.' records
    regions : str
        Restrict to a region, e.g. 'chr1' or 'chr1:1-1000000'
    min_qual : float
        Keep only records with QUAL >= this value
    include_expr : str
        Extra bcftools -i include expression, e.g. 'INFO/AF>0.01'
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
            "operation": operation,
            "vcf_path": vcf_path,
            "pass_only": pass_only,
            "regions": regions,
            "min_qual": min_qual,
            "include_expr": include_expr,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "VCF_count_variants",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["VCF_count_variants"]
