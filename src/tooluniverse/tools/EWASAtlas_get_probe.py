"""
EWASAtlas_get_probe

Get every curated epigenome-wide association study (EWAS) result reported for one Illumina CpG pr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EWASAtlas_get_probe(
    probe_id: str,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get every curated epigenome-wide association study (EWAS) result reported for one Illumina CpG pr...

    Parameters
    ----------
    probe_id : str
        Illumina 450K/EPIC CpG probe ID, e.g. 'cg05575921'.
    limit : int
        Max associations to return, 1-500. Default 50.
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
    _args = {
        k: v for k, v in {"probe_id": probe_id, "limit": limit}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EWASAtlas_get_probe",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EWASAtlas_get_probe"]
