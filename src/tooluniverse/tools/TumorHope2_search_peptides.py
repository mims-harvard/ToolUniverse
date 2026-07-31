"""
TumorHope2_search_peptides

Search TumorHoPe 2 (Raghava lab, IIITD) for TUMOR-HOMING peptide records used in drug delivery. F...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TumorHope2_search_peptides(
    source: Optional[str] = None,
    target_tumor: Optional[str] = None,
    name_source: Optional[str] = None,
    conjugate: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search TumorHoPe 2 (Raghava lab, IIITD) for TUMOR-HOMING peptide records used in drug delivery. F...

    Parameters
    ----------
    source : str
        Peptide source label. Example: 'A33H' -> 1 record (SIWV, a brain-tumor-homing...
    target_tumor : str
        Target tumor type. Example: 'Brain tumor' -> ~39 records.
    name_source : str
        Source name to match.
    conjugate : str
        Conjugate / payload label (e.g. a fluorophore or nanoparticle).
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
            "source": source,
            "target_tumor": target_tumor,
            "name_source": name_source,
            "conjugate": conjugate,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "TumorHope2_search_peptides",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TumorHope2_search_peptides"]
