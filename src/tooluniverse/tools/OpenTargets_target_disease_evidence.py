"""
OpenTargets_target_disease_evidence

Explore IntOGen somatic driver evidence for a target-disease association. IMPORTANT: IntOGen only...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenTargets_target_disease_evidence(
    efoId: Optional[str] = None,
    ensemblId: Optional[str] = None,
    gene_symbol: Optional[str] = None,
    disease_name: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Explore IntOGen somatic driver evidence for a target-disease association. IMPORTANT: IntOGen only...

    Parameters
    ----------
    efoId : str
        EFO/MONDO disease ID (e.g., EFO_0000384). Alternative to disease_name.
    ensemblId : str
        Ensembl gene ID (e.g., ENSG00000141510). Alternative to gene_symbol.
    gene_symbol : str
        HGNC gene symbol (e.g., 'TP53', 'BRCA1'). Auto-resolved to ensemblId.
    disease_name : str
        Disease or phenotype name (e.g., 'Crohn disease', 'breast carcinoma'). Auto-r...
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
        for k, v in {
            "efoId": efoId,
            "ensemblId": ensemblId,
            "gene_symbol": gene_symbol,
            "disease_name": disease_name,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenTargets_target_disease_evidence",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenTargets_target_disease_evidence"]
