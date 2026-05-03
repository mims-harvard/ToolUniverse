"""
eQTL_list_datasets

List available eQTL (expression Quantitative Trait Loci) datasets from the EBI eQTL Catalogue. Ea...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def eQTL_list_datasets(
    size: Optional[int] = 20,
    quant_method: Optional[str | Any] = None,
    tissue_id: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List available eQTL (expression Quantitative Trait Loci) datasets from the EBI eQTL Catalogue. Ea...

    Parameters
    ----------
    size : int
        Number of datasets to return (default 20)
    quant_method : str | Any
        Filter by quantification method: 'ge' (gene expression), 'exon', 'tx' (transc...
    tissue_id : str | Any
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
