"""
AllenBrain_get_expression_datasets

Get gene expression experiment datasets from the Allen Mouse Brain Atlas for a given gene. Return...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def AllenBrain_get_expression_datasets(
    gene_acronym: str,
    product_id: Optional[int] = 1,
    num_rows: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get gene expression experiment datasets from the Allen Mouse Brain Atlas for a given gene. Return...

    Parameters
    ----------
    gene_acronym : str
        Gene symbol/acronym. Examples: 'Gad1', 'Pvalb', 'Sst', 'Bdnf', 'Th', 'Slc17a7'.
    product_id : int
        Product ID for the dataset type. 1=Mouse Brain ISH, 2=Mouse Brain microarray....
    num_rows : int
        Max results to return. Default: 50.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "gene_acronym": gene_acronym,
            "product_id": product_id,
            "num_rows": num_rows,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "AllenBrain_get_expression_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["AllenBrain_get_expression_datasets"]
