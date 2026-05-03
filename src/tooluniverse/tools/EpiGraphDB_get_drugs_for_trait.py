"""
EpiGraphDB_get_drugs_for_trait

Find drugs that target genes associated with a GWAS risk factor trait. Uses genetic evidence to i...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EpiGraphDB_get_drugs_for_trait(
    trait: str,
    pval_threshold: Optional[float] = 0.0001,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Find drugs that target genes associated with a GWAS risk factor trait. Uses genetic evidence to i...

    Parameters
    ----------
    trait : str
        GWAS risk factor trait name (e.g., 'LDL cholesterol', 'Body mass index', 'C-r...
    pval_threshold : float
        GWAS p-value threshold for gene-trait associations (default 1e-4).
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
            "name": "EpiGraphDB_get_drugs_for_trait",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EpiGraphDB_get_drugs_for_trait"]
