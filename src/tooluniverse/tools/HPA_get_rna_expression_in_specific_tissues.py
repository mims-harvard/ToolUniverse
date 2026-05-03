"""
HPA_get_rna_expression_in_specific_tissues

Query RNA expression levels (nTPM) for a specific gene in one or more user-specified tissues with...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HPA_get_rna_expression_in_specific_tissues(
    ensembl_id: str,
    tissue_names: list[str],
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Query RNA expression levels (nTPM) for a specific gene in one or more user-specified tissues with...

    Parameters
    ----------
    ensembl_id : str
        Ensembl Gene ID for the gene, e.g., 'ENSG00000141510' for TP53.
    tissue_names : list[str]
        List of tissue names to query, e.g., ['brain', 'liver', 'heart muscle', 'kidn...
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
        for k, v in {"ensembl_id": ensembl_id, "tissue_names": tissue_names}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HPA_get_rna_expression_in_specific_tissues",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HPA_get_rna_expression_in_specific_tissues"]
