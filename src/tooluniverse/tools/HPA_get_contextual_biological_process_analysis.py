"""
HPA_get_contextual_biological_process_analysis

Analyze a gene's biological processes in the context of a specific tissue or cell line by integra...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HPA_get_contextual_biological_process_analysis(
    gene_name: str,
    context_name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Analyze a gene's biological processes in the context of a specific tissue or cell line by integra...

    Parameters
    ----------
    gene_name : str
        Gene name or symbol, e.g., 'TP53', 'EGFR', 'BRCA1'.
    context_name : str
        Name of the tissue or cell line to provide context, e.g., 'brain', 'liver', '...
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
        k: v
        for k, v in {"gene_name": gene_name, "context_name": context_name}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HPA_get_contextual_biological_process_analysis",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HPA_get_contextual_biological_process_analysis"]
