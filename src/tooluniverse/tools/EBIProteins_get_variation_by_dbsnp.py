"""
EBIProteins_get_variation_by_dbsnp

Reverse variation lookup by dbSNP rsID from the EBI Proteins API. Given a dbSNP rsID, returns eve...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EBIProteins_get_variation_by_dbsnp(
    dbsnp_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Reverse variation lookup by dbSNP rsID from the EBI Proteins API. Given a dbSNP rsID, returns eve...

    Parameters
    ----------
    dbsnp_id : str
        dbSNP reference SNP ID (rsID). Examples: 'rs1042522' (TP53 Pro72Arg), 'rs4293...
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
    _args = {k: v for k, v in {"dbsnp_id": dbsnp_id}.items() if v is not None}
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
