"""
OncoKB_annotate_mutations

Annotate a cancer mutation using OncoKB. Accepts query string like 'BRAF V600E' or separate gene/...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OncoKB_annotate_mutations(
    operation: Optional[str] = None,
    query: Optional[str] = None,
    gene: Optional[str] = None,
    variant: Optional[str] = None,
    tumor_type: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Annotate a cancer mutation using OncoKB. Accepts query string like 'BRAF V600E' or separate gene/...

    Parameters
    ----------
    operation : str
        Operation type (fixed: annotate_variant)
    query : str
        Mutation query string, e.g. 'BRAF V600E' or 'EGFR T790M'. Gene and variant se...
    gene : str
        Gene symbol (e.g., BRAF, EGFR, TP53)
    variant : str
        Protein change (e.g., V600E, T790M)
    tumor_type : str
        Optional OncoTree tumor type code (e.g., MEL, LUAD)
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
        for k, v in {
            "operation": operation,
            "query": query,
            "gene": gene,
            "variant": variant,
            "tumor_type": tumor_type,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OncoKB_annotate_mutations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OncoKB_annotate_mutations"]
