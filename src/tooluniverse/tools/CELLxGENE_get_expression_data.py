"""
CELLxGENE_get_expression_data

Query gene expression data from CELLxGENE Census (50M+ cells, 60K+ genes). CRITICAL: At least one...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CELLxGENE_get_expression_data(
    operation: str,
    organism: Optional[str] = "Homo sapiens",
    obs_value_filter: Optional[str] = None,
    var_value_filter: Optional[str] = None,
    obs_column_names: Optional[list[str]] = None,
    var_column_names: Optional[list[str]] = None,
    census_version: Optional[str] = "stable",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Optional[dict[str, Any]]:
    """
    Query gene expression data from CELLxGENE Census (50M+ cells, 60K+ genes). CRITICAL: At least one...

    Parameters
    ----------
    operation : str
        Operation type
    organism : str
        Organism name
    obs_value_filter : str
        REQUIRED (or use var_value_filter) - Cell filter. Common values: tissue_gener...
    var_value_filter : str
        REQUIRED (or use obs_value_filter) - Gene filter by symbol or Ensembl ID. Exa...
    obs_column_names : list[str]
        Cell metadata columns to include
    var_column_names : list[str]
        Gene metadata columns to include
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
    Optional[dict[str, Any]]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "organism": organism,
            "obs_value_filter": obs_value_filter,
            "var_value_filter": var_value_filter,
            "obs_column_names": obs_column_names,
            "var_column_names": var_column_names,
            "census_version": census_version,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CELLxGENE_get_expression_data",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CELLxGENE_get_expression_data"]
