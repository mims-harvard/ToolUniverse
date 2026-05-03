"""
WormBase_get_phenotypes

Get phenotype annotations for a C. elegans gene from WormBase. Returns observed phenotypes (from ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def WormBase_get_phenotypes(
    gene_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get phenotype annotations for a C. elegans gene from WormBase. Returns observed phenotypes (from ...

    Parameters
    ----------
    gene_id : str
        WormBase gene identifier. Examples: 'WBGene00006763' (unc-26), 'WBGene0000089...
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
    _args = {k: v for k, v in {"gene_id": gene_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "WormBase_get_phenotypes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["WormBase_get_phenotypes"]
