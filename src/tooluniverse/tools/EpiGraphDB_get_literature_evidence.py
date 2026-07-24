"""
EpiGraphDB_get_literature_evidence

Get SemMedDB literature triple evidence supporting a GWAS trait via EpiGraphDB. Returns subject-p...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EpiGraphDB_get_literature_evidence(
    trait: str,
    pval_threshold: Optional[float] = 1e-08,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get SemMedDB literature triple evidence supporting a GWAS trait via EpiGraphDB. Returns subject-p...

    Parameters
    ----------
    trait : str
        GWAS trait name (e.g., 'body mass index', 'LDL cholesterol', 'coronary heart ...
    pval_threshold : float
        GWAS p-value threshold for the trait's GWAS hits (default 1e-8).
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
        for k, v in {"trait": trait, "pval_threshold": pval_threshold}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EpiGraphDB_get_literature_evidence",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EpiGraphDB_get_literature_evidence"]
