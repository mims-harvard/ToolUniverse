"""
PubChemBioAssay_get_concise_activity_table

Get the assay-wide concise bioactivity table for a PubChem BioAssay (AID). Returns ONE row per te...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubChemBioAssay_get_concise_activity_table(
    aid: int,
    max_rows: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the assay-wide concise bioactivity table for a PubChem BioAssay (AID). Returns ONE row per te...

    Parameters
    ----------
    aid : int
        PubChem BioAssay ID (AID). Examples: 504832 (malaria qHTS, 305803 rows), 1259...
    max_rows : int
        Maximum number of compound rows to return in the payload (default 1000, max 1...
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
        k: v for k, v in {"aid": aid, "max_rows": max_rows}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PubChemBioAssay_get_concise_activity_table",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubChemBioAssay_get_concise_activity_table"]
