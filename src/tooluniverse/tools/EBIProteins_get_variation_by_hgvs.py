"""
EBIProteins_get_variation_by_hgvs

Reverse variation lookup by HGVS genomic expression from the EBI Proteins API. Given an HGVS geno...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EBIProteins_get_variation_by_hgvs(
    hgvs: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Reverse variation lookup by HGVS genomic expression from the EBI Proteins API. Given an HGVS geno...

    Parameters
    ----------
    hgvs : str
        HGVS genomic expression using a RefSeq NC_ accession. Example: 'NC_000017.11:...
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
            "name": "EBIProteins_get_variation_by_hgvs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EBIProteins_get_variation_by_hgvs"]
