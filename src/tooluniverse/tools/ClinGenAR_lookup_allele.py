"""
ClinGenAR_lookup_allele

Look up a genetic variant in the ClinGen Allele Registry by HGVS notation. Returns the canonical ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinGenAR_lookup_allele(
    hgvs: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Look up a genetic variant in the ClinGen Allele Registry by HGVS notation. Returns the canonical ...

    Parameters
    ----------
    hgvs : str
        HGVS expression for the variant. Supports coding (c.), genomic (g.), and prot...
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
    _args = {k: v for k, v in {"hgvs": hgvs}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ClinGenAR_lookup_allele",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinGenAR_lookup_allele"]
