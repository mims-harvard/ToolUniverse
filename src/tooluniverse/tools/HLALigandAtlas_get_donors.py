"""
HLALigandAtlas_get_donors

Retrieve the donor-to-HLA-allele mapping table from the HLA Ligand Atlas (hla-ligand-atlas.org, r...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HLALigandAtlas_get_donors(
    donor: Optional[str] = None,
    allele: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve the donor-to-HLA-allele mapping table from the HLA Ligand Atlas (hla-ligand-atlas.org, r...

    Parameters
    ----------
    donor : str
        Donor identifier substring to match, e.g. 'AUT01' or 'AUT01-DN13'. Leave empt...
    allele : str
        HLA allele substring to match, e.g. 'A*11:01' or 'A*11'. Leave empty for all ...
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
        k: v for k, v in {"donor": donor, "allele": allele}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HLALigandAtlas_get_donors",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HLALigandAtlas_get_donors"]
