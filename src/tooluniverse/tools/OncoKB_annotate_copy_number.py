"""
OncoKB_annotate_copy_number

Annotate copy number alterations (amplification/deletion) for oncogenic potential. Returns eviden...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OncoKB_annotate_copy_number(
    gene: str,
    operation: Optional[str] = None,
    copy_number_type: Optional[str] = None,
    tumor_type: Optional[str] = None,
    copy_number_alteration: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Annotate copy number alterations (amplification/deletion) for oncogenic potential. Returns eviden...

    Parameters
    ----------
    operation : str
        Operation type (fixed: annotate_copy_number)
    gene : str
        Gene symbol (e.g., ERBB2, MYC, CDKN2A)
    copy_number_type : str
        Type of copy number alteration (case-insensitive: AMPLIFICATION or DELETION)
    tumor_type : str
        Optional OncoTree tumor type code
    copy_number_alteration : str
        Alias for copy_number_type. Amplification or Deletion.
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
            "operation": operation,
            "gene": gene,
            "copy_number_type": copy_number_type,
            "tumor_type": tumor_type,
            "copy_number_alteration": copy_number_alteration,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OncoKB_annotate_copy_number",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OncoKB_annotate_copy_number"]
