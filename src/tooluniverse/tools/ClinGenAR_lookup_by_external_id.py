"""
ClinGenAR_lookup_by_external_id

Reverse-lookup the ClinGen Allele Registry by an external identifier. Given a dbSNP rsID (dbsnp_r...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinGenAR_lookup_by_external_id(
    dbsnp_rs: Optional[str | int] = None,
    clinvar_variation_id: Optional[str | int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Reverse-lookup the ClinGen Allele Registry by an external identifier. Given a dbSNP rsID (dbsnp_r...

    Parameters
    ----------
    dbsnp_rs : str | int
        dbSNP rsID to resolve. The 'rs' prefix is optional (e.g. 113488022 or 'rs1134...
    clinvar_variation_id : str | int
        ClinVar VariationID to resolve (e.g. 13961). Mutually exclusive with dbsnp_rs.
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
            "dbsnp_rs": dbsnp_rs,
            "clinvar_variation_id": clinvar_variation_id,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ClinGenAR_lookup_by_external_id",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinGenAR_lookup_by_external_id"]
