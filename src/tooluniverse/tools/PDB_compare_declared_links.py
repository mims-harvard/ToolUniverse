"""
PDB_compare_declared_links

Compare explicit reference PDB LINK distances against a local PDB model. Resolves exact atoms wit...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PDB_compare_declared_links(
    reference_pdb_path: Optional[str] = None,
    reference_pdb_content: Optional[str] = None,
    reference_model_index: Optional[int] = None,
    observed_pdb_path: Optional[str] = None,
    observed_pdb_content: Optional[str] = None,
    observed_model_index: Optional[int] = None,
    max_length_error_angstrom: Optional[float] = None,
    chain_map: Optional[dict[str, Any]] = None,
    residue_map: Optional[list[Any]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Compare explicit reference PDB LINK distances against a local PDB model. Resolves exact atoms wit...

    Parameters
    ----------
    reference_pdb_path : str
        Local reference legacy PDB path; exactly one path or content for this input. ...
    reference_pdb_content : str
        Local reference legacy PDB content; exactly one path or content for this inpu...
    reference_model_index : int
        Select model by file order, default1; models never pooled.
    observed_pdb_path : str
        Local observed legacy PDB path; exactly one path or content for this input. N...
    observed_pdb_content : str
        Local observed legacy PDB content; exactly one path or content for this input...
    observed_model_index : int
        Select model by file order, default1; models never pooled.
    max_length_error_angstrom : float
        Maximum absolute deviation from reference coordinate distance, default0.3 Ang...
    chain_map : dict[str, Any]
        Explicit reference-to-observed chain map, default identity. A blank PDB chain...
    residue_map : list[Any]
        Explicit residue-number/insertion remapping within the chain map. Unmapped re...
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
            "reference_pdb_path": reference_pdb_path,
            "reference_pdb_content": reference_pdb_content,
            "reference_model_index": reference_model_index,
            "observed_pdb_path": observed_pdb_path,
            "observed_pdb_content": observed_pdb_content,
            "observed_model_index": observed_model_index,
            "max_length_error_angstrom": max_length_error_angstrom,
            "chain_map": chain_map,
            "residue_map": residue_map,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PDB_compare_declared_links",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PDB_compare_declared_links"]
