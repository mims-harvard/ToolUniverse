"""
HPA_get_cancer_prognostics_by_gene

Retrieve prognostic value of a gene across various cancer types, indicating if its expression lev...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HPA_get_cancer_prognostics_by_gene(
    ensembl_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve prognostic value of a gene across various cancer types, indicating if its expression lev...

    Parameters
    ----------
    ensembl_id : str
        Ensembl Gene ID of the gene to check, e.g., 'ENSG00000141510' for TP53, 'ENSG...
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
    _args = {k: v for k, v in {"ensembl_id": ensembl_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "HPA_get_cancer_prognostics_by_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HPA_get_cancer_prognostics_by_gene"]
