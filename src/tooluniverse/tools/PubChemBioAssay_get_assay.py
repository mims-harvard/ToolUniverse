"""
PubChemBioAssay_get_assay

Get detailed description of a PubChem BioAssay by its AID (Assay ID). PubChem BioAssay stores ove...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubChemBioAssay_get_assay(
    aid: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed description of a PubChem BioAssay by its AID (Assay ID). PubChem BioAssay stores ove...

    Parameters
    ----------
    aid : int
        PubChem BioAssay ID (AID). Examples: 1234 (Redox Cycling H2O2 assay), 1259393...
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
    _args = {k: v for k, v in {"aid": aid}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PubChemBioAssay_get_assay",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubChemBioAssay_get_assay"]
