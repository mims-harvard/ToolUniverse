"""
KEGG_get_disease_genes

Get all human genes linked to a KEGG disease. Returns KEGG gene IDs (hsa:XXXXX format) for genes ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def KEGG_get_disease_genes(
    disease_id: str,
    organism: Optional[str] = "hsa",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get all human genes linked to a KEGG disease. Returns KEGG gene IDs (hsa:XXXXX format) for genes ...

    Parameters
    ----------
    disease_id : str
        KEGG disease ID (e.g., 'H00001' for B-cell ALL, 'H00031' for breast cancer).
    organism : str
        KEGG organism code (default: 'hsa' for human). Other examples: 'mmu' (mouse).
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
        for k, v in {"disease_id": disease_id, "organism": organism}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "KEGG_get_disease_genes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["KEGG_get_disease_genes"]
