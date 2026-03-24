"""
ClinGenAllele_lookup_hgvs

Look up a genetic variant by HGVS expression in the ClinGen Allele Registry to get its canonical ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinGenAllele_lookup_hgvs(
    hgvs: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Look up a genetic variant by HGVS expression in the ClinGen Allele Registry to get its canonical ...

    Parameters
    ----------
    hgvs : str
        HGVS expression for the variant. Examples: 'NC_000017.11:g.7674220C>T' (genom...
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
    _args = {k: v for k, v in {"hgvs": hgvs}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ClinGenAllele_lookup_hgvs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinGenAllele_lookup_hgvs"]
