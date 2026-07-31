"""
Network_proximity

Graph distance between two node sets on a user-supplied network, with the standard measures from ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Network_proximity(
    edges: Optional[list[Any]] = None,
    edgelist_path: Optional[str] = None,
    set_a: Optional[list[str]] = None,
    set_b: Optional[list[str]] = None,
    targets: Optional[list[str]] = None,
    disease_genes: Optional[list[str]] = None,
    measure: Optional[str] = None,
    n_rand: Optional[int] = None,
    seed: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Graph distance between two node sets on a user-supplied network, with the standard measures from ...

    Parameters
    ----------
    edges : list[Any]
        Network as inline [source, target] node-id pairs (undirected). Use for small/...
    edgelist_path : str
        Alternative to inline: path to a 2-column edgelist (.tsv/.txt = tab, else comma)
    set_a : list[str]
        First node set
    set_b : list[str]
        Second node set
    targets : list[str]
        Alias for set_a (drug targets)
    disease_genes : list[str]
        Alias for set_b (disease-module genes)
    measure : str
        Distance measure: 'closest' (default, Guney), 'shortest' (all-pairs mean), or...
    n_rand : int
        Degree-matched randomizations for the null (default 1000)
    seed : int
        Random seed for reproducibility (default 42)
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
            "edges": edges,
            "edgelist_path": edgelist_path,
            "set_a": set_a,
            "set_b": set_b,
            "targets": targets,
            "disease_genes": disease_genes,
            "measure": measure,
            "n_rand": n_rand,
            "seed": seed,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Network_proximity",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Network_proximity"]
