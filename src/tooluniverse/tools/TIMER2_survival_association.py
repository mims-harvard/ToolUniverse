"""
TIMER2_survival_association

Analyze overall survival association of gene expression in TCGA cancer patients using cBioPortal ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TIMER2_survival_association(
    operation: str,
    cancer: str,
    gene: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Analyze overall survival association of gene expression in TCGA cancer patients using cBioPortal ...

    Parameters
    ----------
    operation : str
        Operation type
    cancer : str
        TCGA cancer type (e.g., 'BRCA', 'LUAD', 'COAD')
    gene : str
        Gene symbol for survival analysis (e.g., 'CD8A', 'TP53', 'BRCA1')
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

    return get_shared_client().run_one_function(
        {
            "name": "TIMER2_survival_association",
            "arguments": {"operation": operation, "cancer": cancer, "gene": gene},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TIMER2_survival_association"]
