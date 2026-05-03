"""
MyGene_get_gene_annotation

Get detailed annotation for a specific gene by its ID (Entrez or Ensembl). Returns comprehensive ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MyGene_get_gene_annotation(
    gene_id: str,
    fields: Optional[
        str
    ] = "symbol,name,entrezgene,ensembl,summary,go,pathway,interpro",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed annotation for a specific gene by its ID (Entrez or Ensembl). Returns comprehensive ...

    Parameters
    ----------
    gene_id : str
        Gene ID to query. Can be Entrez Gene ID (e.g., '1017' for CDK2) or Ensembl ID...
    fields : str
        Comma-separated list of fields to return. Available fields include: symbol, n...
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
        k: v for k, v in {"gene_id": gene_id, "fields": fields}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MyGene_get_gene_annotation",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MyGene_get_gene_annotation"]
