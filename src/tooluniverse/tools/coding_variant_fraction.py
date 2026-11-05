"""
coding_variant_fraction

Compute the fraction of CODING variants in an Excel/CSV variant table that match a given Sequence...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def coding_variant_fraction(
    file: str,
    vaf_threshold: Optional[float] = None,
    annotation: Optional[str] = None,
    header_rows: Optional[int] = None,
    vaf_col: Optional[str] = None,
    so_col: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Compute the fraction of CODING variants in an Excel/CSV variant table that match a given Sequence...

    Parameters
    ----------
    file : str
        Path to variant Excel (.xlsx) or CSV file.
    vaf_threshold : float
        Keep variants with VAF strictly less than this value. Default 0.3.
    annotation : str
        Sequence Ontology term to count in numerator. Default 'synonymous_variant'.
    header_rows : int
        1 for flat headers, 2 for MultiIndex (common in Excel variant reports). Defau...
    vaf_col : str
        Explicit VAF column name. If empty, auto-detect from 'variant allele freq' or...
    so_col : str
        Explicit Sequence Ontology column name. If empty, auto-detect from 'sequence ...
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
            "file": file,
            "vaf_threshold": vaf_threshold,
            "annotation": annotation,
            "header_rows": header_rows,
            "vaf_col": vaf_col,
            "so_col": so_col,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "coding_variant_fraction",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["coding_variant_fraction"]
