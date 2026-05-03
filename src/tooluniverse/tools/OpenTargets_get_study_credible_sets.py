"""
OpenTargets_get_study_credible_sets

Get all credible sets (fine-mapped GWAS loci) for a specific GWAS study from Open Targets. Return...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenTargets_get_study_credible_sets(
    studyIds: list[str],
    size: Optional[int] = 20,
    index: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get all credible sets (fine-mapped GWAS loci) for a specific GWAS study from Open Targets. Return...

    Parameters
    ----------
    studyIds : list[str]
        GWAS study accession IDs (e.g., ['GCST000392'])
    size : int
        Number of credible sets to return (default 20)
    index : int
        Page index for pagination (0-based, default 0)
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
        for k, v in {"studyIds": studyIds, "size": size, "index": index}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenTargets_get_study_credible_sets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenTargets_get_study_credible_sets"]
