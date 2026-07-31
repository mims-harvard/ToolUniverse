"""
MetabolomicsWorkbench_get_gene_protein

Look up a Metabolomics Workbench gene or protein (MGP) annotation record linking gene/protein ide...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MetabolomicsWorkbench_get_gene_protein(
    input_value: str,
    entity: Optional[str] = None,
    id_type: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Look up a Metabolomics Workbench gene or protein (MGP) annotation record linking gene/protein ide...

    Parameters
    ----------
    input_value : str
        The identifier to look up (e.g. gene symbol 'acaca', UniProt id 'Q13085', mgp...
    entity : str
        Which record type to fetch: 'gene' (default) or 'protein'.
    id_type : str
        Namespace of input_value. For genes: gene_symbol (default), gene_id, gene_nam...
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
            "input_value": input_value,
            "entity": entity,
            "id_type": id_type,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MetabolomicsWorkbench_get_gene_protein",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MetabolomicsWorkbench_get_gene_protein"]
