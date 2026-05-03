"""
OpenTargets_get_target_gene_ontology_by_ensemblID

Retrieve Gene Ontology annotations for a specific target by Ensembl ID.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenTargets_get_target_gene_ontology_by_ensemblID(
    ensemblId: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve Gene Ontology annotations for a specific target by Ensembl ID.

    Parameters
    ----------
    ensemblId : str
        The Ensembl ID of the target for which to retrieve Gene Ontology annotations.
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
    _args = {k: v for k, v in {"ensemblId": ensemblId}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OpenTargets_get_target_gene_ontology_by_ensemblID",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenTargets_get_target_gene_ontology_by_ensemblID"]
