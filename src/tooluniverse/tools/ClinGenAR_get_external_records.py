"""
ClinGenAR_get_external_records

Get detailed cross-references and external database records for a ClinGen canonical allele. Takes...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinGenAR_get_external_records(
    allele_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed cross-references and external database records for a ClinGen canonical allele. Takes...

    Parameters
    ----------
    allele_id : str
        ClinGen canonical allele ID. Examples: 'CA000387' (TP53 R248Q), 'CA006116' (B...
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
    _args = {k: v for k, v in {"allele_id": allele_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ClinGenAR_get_external_records",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinGenAR_get_external_records"]
