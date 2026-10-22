"""
eQTL_list_datasets

List available eQTL (expression Quantitative Trait Loci) datasets from the EBI eQTL Catalogue. Re...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def eQTL_list_datasets(
    size: Optional[int] = 20,
    start: Optional[int] = 0,
    quant_method: Optional[str] = None,
    tissue_id: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List available eQTL (expression Quantitative Trait Loci) datasets from the EBI eQTL Catalogue. Re...

    Parameters
    ----------
    size : int
        Page size from 1 to 999 (default 20; one upstream slot is reserved for lookah...
    start : int
        Zero-based dataset offset. Continue with metadata.next_start while metadata.h...
    quant_method : str
        Filter by quantification method: 'ge' (gene expression), 'exon', 'tx' (transc...
    tissue_id : str
        Filter by tissue ontology ID (e.g., 'CL_0000235' for macrophage, 'UBERON_0002...
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
            "size": size,
            "start": start,
            "quant_method": quant_method,
            "tissue_id": tissue_id,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "eQTL_list_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["eQTL_list_datasets"]
