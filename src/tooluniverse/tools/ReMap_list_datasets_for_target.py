"""
ReMap_list_datasets_for_target

List ReMap ChIP-seq datasets for a transcription factor, one row per dataset, optionally filtered...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ReMap_list_datasets_for_target(
    target: str,
    taxid: Optional[int] = 9606,
    experiment: Optional[str] = None,
    count_peaks: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List ReMap ChIP-seq datasets for a transcription factor, one row per dataset, optionally filtered...

    Parameters
    ----------
    target : str
        Transcription factor / target name, e.g. 'FOXA1'.
    taxid : int
        NCBI taxonomy id. Default 9606 (human).
    experiment : str
        Optional experiment accession prefix to filter on, e.g. 'GSE23852'. Dataset n...
    count_peaks : bool
        Download each dataset's BED and report its peak count. Slower; use when the q...
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
            "target": target,
            "taxid": taxid,
            "experiment": experiment,
            "count_peaks": count_peaks,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ReMap_list_datasets_for_target",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ReMap_list_datasets_for_target"]
