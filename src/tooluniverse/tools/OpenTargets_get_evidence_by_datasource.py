"""
OpenTargets_get_evidence_by_datasource

Get target-disease evidence from Open Targets filtered by configurable data sources. Unlike OpenT...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenTargets_get_evidence_by_datasource(
    efoId: Optional[str] = None,
    ensemblId: Optional[str] = None,
    gene_symbol: Optional[str] = None,
    disease_name: Optional[str] = None,
    datasourceIds: Optional[list[str]] = None,
    size: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get target-disease evidence from Open Targets filtered by configurable data sources. Unlike OpenT...

    Parameters
    ----------
    efoId : str
        Disease EFO ID (e.g., 'EFO_0000384' for Crohn's disease). Alternative to dise...
    ensemblId : str
        Target Ensembl gene ID (e.g., 'ENSG00000141510' for TP53). Alternative to gen...
    gene_symbol : str
        HGNC gene symbol (e.g., 'TP53', 'BRCA1'). Auto-resolved to ensemblId.
    disease_name : str
        Disease or phenotype name (e.g., 'Crohn disease'). Auto-resolved to efoId.
    datasourceIds : list[str]
        List of datasource IDs to filter evidence. Examples: ['chembl', 'europepmc'],...
    size : int
        Maximum evidence rows to return (default: 50)
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
            "datasourceIds": datasourceIds,
            "size": size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenTargets_get_evidence_by_datasource",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenTargets_get_evidence_by_datasource"]
