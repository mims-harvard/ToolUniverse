"""
CELLxGENE_get_gene_metadata

Query gene (variable) metadata from CELLxGENE Census. Returns gene symbols, Ensembl IDs, feature ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CELLxGENE_get_gene_metadata(
    operation: str,
    organism: Optional[str] = "Homo sapiens",
    var_value_filter: Optional[str] = None,
    column_names: Optional[list[str]] = None,
    census_version: Optional[str] = "stable",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Optional[list[Any]]:
    """
    Query gene (variable) metadata from CELLxGENE Census. Returns gene symbols, Ensembl IDs, feature ...

    Parameters
    ----------
    operation : str
        Operation type
    organism : str
        Organism name
    var_value_filter : str
        Filter genes using SQL-like syntax. Format: 'field == "value"'. Common fields...
    column_names : list[str]
        Specific columns to return (default: all columns)
    census_version : str
        Census version to query. 'stable' (recommended, Long-Term Support release), '...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Optional[list[Any]]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "organism": organism,
            "var_value_filter": var_value_filter,
            "column_names": column_names,
            "census_version": census_version,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CELLxGENE_get_gene_metadata",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CELLxGENE_get_gene_metadata"]
