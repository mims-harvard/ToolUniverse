"""
ENCORI_get_RBP_disease

Retrieve RBP-disease associations via ENCORI (starBase) RBPDisease module: RBP binding sites that...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ENCORI_get_RBP_disease(
    gene: Optional[str] = None,
    rbp: Optional[str] = None,
    tissue: Optional[str] = None,
    disease: Optional[str] = None,
    assembly: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve RBP-disease associations via ENCORI (starBase) RBPDisease module: RBP binding sites that...

    Parameters
    ----------
    gene : str
        Bound target gene symbol, e.g. 'MYC' (alias: 'gene_symbol').
    rbp : str
        RNA-binding protein symbol, e.g. 'ACIN1' (alias: 'RBP').
    tissue : str
        Tissue filter, e.g. 'breast', 'lung', 'liver'.
    disease : str
        Disease keyword, e.g. 'carcinoma', 'adenocarcinoma'.
    assembly : str
        Genome assembly (default 'hg38').
    limit : int
        Maximum association rows to return (1-500, default 100).
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
            "gene": gene,
            "rbp": rbp,
            "tissue": tissue,
            "disease": disease,
            "assembly": assembly,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ENCORI_get_RBP_disease",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ENCORI_get_RBP_disease"]
