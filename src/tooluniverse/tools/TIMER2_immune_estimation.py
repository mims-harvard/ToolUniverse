"""
TIMER2_immune_estimation

Estimate immune cell abundance in TCGA cancer samples using TIMER-equivalent marker gene expressi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TIMER2_immune_estimation(
    operation: str,
    cancer: str,
    gene: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Estimate immune cell abundance in TCGA cancer samples using TIMER-equivalent marker gene expressi...

    Parameters
    ----------
    operation : str
        Operation type
    cancer : str
        TCGA cancer type abbreviation (e.g., 'BRCA', 'LUAD', 'COAD', 'SKCM', 'GBM')
    gene : str | Any
        Optional gene symbol to correlate with immune infiltration (e.g., 'CD8A', 'PD...
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
            "name": "TIMER2_immune_estimation",
            "arguments": {"operation": operation, "cancer": cancer, "gene": gene},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TIMER2_immune_estimation"]
