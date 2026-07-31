"""
read_executed_notebook

Read a pre-executed Jupyter notebook (.ipynb, often named '*_executed.ipynb') and return its cell...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def read_executed_notebook(
    data_folder: Optional[str] = None,
    notebook_path: Optional[str] = None,
    search: Optional[str] = None,
    regex: Optional[bool] = None,
    max_output_chars: Optional[int] = None,
    include_source: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Read a pre-executed Jupyter notebook (.ipynb, often named '*_executed.ipynb') and return its cell...

    Parameters
    ----------
    data_folder : str
        Directory to search (recursively) for a .ipynb file. Prefers *_executed.ipynb...
    notebook_path : str
        Direct path to a specific .ipynb file. Provide either this OR data_folder.
    search : str
        Optional: comma-separated terms (or regex if regex=true). Cells whose source ...
    regex : bool
        Treat 'search' as a Python regex instead of a comma-separated term list (defa...
    max_output_chars : int
        Truncate each cell source/output to this many characters (default 400)
    include_source : bool
        Include cell source code in the response (default true). Set false to halve r...
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
            "data_folder": data_folder,
            "notebook_path": notebook_path,
            "search": search,
            "regex": regex,
            "max_output_chars": max_output_chars,
            "include_source": include_source,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "read_executed_notebook",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["read_executed_notebook"]
