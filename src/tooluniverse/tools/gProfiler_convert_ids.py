"""
gProfiler_convert_ids

Convert gene identifiers between different namespaces using g:Profiler (g:Convert) from the Unive...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def gProfiler_convert_ids(
    gene_list: str,
    target_namespace: Optional[str] = None,
    organism: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Convert gene identifiers between different namespaces using g:Profiler (g:Convert) from the Unive...

    Parameters
    ----------
    gene_list : str
        Comma-separated list of gene identifiers to convert. Examples: 'TP53,BRCA1,EG...
    target_namespace : str
        Target namespace for conversion. Default: 'ENSG'. Options: ENSG (Ensembl Gene...
    organism : str
        Organism identifier. Default: 'hsapiens'. Examples: 'hsapiens', 'mmusculus'.
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
            "gene_list": gene_list,
            "target_namespace": target_namespace,
            "organism": organism,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "gProfiler_convert_ids",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["gProfiler_convert_ids"]
