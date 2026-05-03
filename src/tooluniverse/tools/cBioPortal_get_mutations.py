"""
cBioPortal_get_mutations

Get mutation data for specific genes in a cancer study. This uses the updated cBioPortal API that...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def cBioPortal_get_mutations(
    study_id: str,
    gene_list: str,
    sample_list_id: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get mutation data for specific genes in a cancer study. This uses the updated cBioPortal API that...

    Parameters
    ----------
    study_id : str
        Cancer study ID (e.g., 'brca_tcga')
    gene_list : str
        Comma-separated gene symbols (e.g., 'BRCA1,BRCA2')
    sample_list_id : str
        Optional sample list ID. If not provided, uses all samples in the study.
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
            "study_id": study_id,
            "gene_list": gene_list,
            "sample_list_id": sample_list_id,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "cBioPortal_get_mutations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["cBioPortal_get_mutations"]
