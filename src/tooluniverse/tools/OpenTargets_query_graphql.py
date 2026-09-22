"""
OpenTargets_query_graphql

Run any read-only GraphQL query against the Open Targets Platform API (targets, diseases, drugs, ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenTargets_query_graphql(
    query: str,
    variables: Optional[dict[str, Any] | str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Run any read-only GraphQL query against the Open Targets Platform API (targets, diseases, drugs, ...

    Parameters
    ----------
    query : str
        GraphQL query document, e.g. '{ target(ensemblId: "ENSG00000141510") { approv...
    variables : dict[str, Any] | str
        Variables for a parameterised query, as a JSON object (or a JSON string)
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
        for k, v in {"query": query, "variables": variables}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OpenTargets_query_graphql",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenTargets_query_graphql"]
