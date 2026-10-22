"""
EBIProteins_get_variation_by_dbsnp

Reverse variation lookup by dbSNP rsID from the EBI Proteins API. Returns every affected UniProt ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EBIProteins_get_variation_by_dbsnp(
    dbsnp_id: str,
    xref_offset: Optional[int] = 0,
    xref_limit: Optional[int] = 5,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Reverse variation lookup by dbSNP rsID from the EBI Proteins API. Returns every affected UniProt ...

    Parameters
    ----------
    dbsnp_id : str
        dbSNP reference SNP ID (rsID). Examples: 'rs1042522' (TP53 Pro72Arg), 'rs4293...
    xref_offset : int
        Zero-based xref offset applied within every returned variant feature.
    xref_limit : int
        Cross-references returned per feature (default 5, maximum 500).
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
            "dbsnp_id": dbsnp_id,
            "xref_offset": xref_offset,
            "xref_limit": xref_limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EBIProteins_get_variation_by_dbsnp",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EBIProteins_get_variation_by_dbsnp"]
