"""
PKAI_predict_sidechain_pka

Predict six protein side-chain pKa types from one PDB with local CPU pKAI/pKAI+ weights. Returns ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PKAI_predict_sidechain_pka(
    pdb_id: Optional[str] = None,
    pdb_path: Optional[str] = None,
    pdb_content: Optional[str] = None,
    python_executable: Optional[str] = None,
    model_variant: Optional[str] = None,
    threads: Optional[int] = None,
    timeout_seconds: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Predict six protein side-chain pKa types from one PDB with local CPU pKAI/pKAI+ weights. Returns ...

    Parameters
    ----------
    pdb_id : str
        Public four-character RCSB PDB ID; alternative to pdb_path/pdb_content. Only ...
    pdb_path : str
        Local single-model PDB file; no upload. Alternative to pdb_id/pdb_content.
    pdb_content : str
        Single-model PDB text; processed locally without upload. Alternative to pdb_i...
    python_executable : str
        Optional same-host Python interpreter with pKAI and torch installed; default ...
    model_variant : str
        pKAI+ (default) for single-structure diagnostics; pKAI for conformation sensi...
    threads : int
        CPU threads, default1.
    timeout_seconds : int
        Finite worker timeout in seconds, default180.
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
            "pdb_id": pdb_id,
            "pdb_path": pdb_path,
            "pdb_content": pdb_content,
            "python_executable": python_executable,
            "model_variant": model_variant,
            "threads": threads,
            "timeout_seconds": timeout_seconds,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PKAI_predict_sidechain_pka",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PKAI_predict_sidechain_pka"]
