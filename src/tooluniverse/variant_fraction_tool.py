"""Coding variant fraction tool.

The implementation is inlined below rather than loaded from
``skills/tooluniverse-variant-analysis/scripts/variant_fraction.py`` at
runtime: that path is resolved relative to the repository root, so it does not
exist under site-packages and the tool failed for every install from PyPI.
"""

from __future__ import annotations

import os
from typing import Any, Dict

import pandas as pd

from .base_tool import BaseTool
from .tool_registry import register_tool


CODING_SO_TERMS = {
    "synonymous_variant",
    "missense_variant",
    "splice_region_variant",
    "stop_gained",
    "stop_lost",
    "start_lost",
    "frameshift_variant",
    "inframe_insertion",
    "inframe_deletion",
}


NON_CODING_SO_TERMS = {
    "intron_variant",
    "3_prime_UTR_variant",
    "5_prime_UTR_variant",
    "upstream_gene_variant",
    "downstream_gene_variant",
    "intergenic_variant",
}


def compute_variant_fraction(
    file_path: str,
    vaf_threshold: float = 0.3,
    annotation: str = "synonymous_variant",
    header_rows: int = 1,
    vaf_col: str = "",
    so_col: str = "",
) -> dict:
    """Compute fraction of variants with a specific annotation.

    Uses CODING variants as denominator (synonymous, missense, splice_region,
    stop_gained/lost, start_lost, frameshift, inframe indels).

    Returns dict with: total_variants, vaf_filtered, coding_variants_below_vaf,
    matching_annotation, fraction, naive_fraction, vaf_column, so_column.
    """
    # Load file
    if file_path.endswith(".xlsx"):
        if header_rows == 2:
            df = pd.read_excel(file_path, header=[0, 1])
        else:
            df = pd.read_excel(file_path)
    else:
        df = pd.read_csv(file_path)

    total = len(df)
    print(f"Loaded: {df.shape}")
    print(f"Columns: {list(df.columns)[:10]}")

    # Auto-detect VAF and SO columns if not provided
    if not vaf_col:
        for col in df.columns:
            col_str = str(col).lower()
            if "variant allele freq" in col_str or "vaf" in col_str:
                vaf_col = col
                break

    if not so_col:
        for col in df.columns:
            col_str = str(col).lower()
            if "sequence ontology" in col_str:
                so_col = col
                break

    if not vaf_col or not so_col:
        raise ValueError(
            f"Could not find VAF column ({vaf_col}) or SO column ({so_col}). "
            f"Available columns: {list(df.columns)}"
        )

    print(f"VAF column: {vaf_col}")
    print(f"SO column: {so_col}")

    # Filter by VAF threshold
    df_filtered = df[pd.to_numeric(df[vaf_col], errors="coerce") < vaf_threshold]
    print(f"Variants with VAF < {vaf_threshold}: {len(df_filtered)}")

    # Filter to coding variants only
    coding_mask = (
        df_filtered[so_col]
        .astype(str)
        .apply(lambda x: any(term in x for term in CODING_SO_TERMS))
    )
    df_coding = df_filtered[coding_mask]
    print(f"Coding variants: {len(df_coding)}")

    # Count target annotation
    target_mask = df_coding[so_col].astype(str).str.contains(annotation, na=False)
    n_target = int(target_mask.sum())
    fraction = n_target / len(df_coding) if len(df_coding) > 0 else 0.0
    naive = n_target / len(df_filtered) if len(df_filtered) > 0 else 0.0

    print(f"{annotation}: {n_target}")
    print(f"Fraction (coding denominator): {fraction:.4f}")
    print(f"For comparison, naive fraction (all variants): {naive:.4f}")

    return {
        "total_variants": int(total),
        "vaf_filtered": int(len(df_filtered)),
        "coding_variants_below_vaf": int(len(df_coding)),
        "matching_annotation": n_target,
        "fraction": float(fraction),
        "naive_fraction": float(naive),
        "vaf_column": str(vaf_col),
        "so_column": str(so_col),
        "vaf_threshold": float(vaf_threshold),
        "annotation": str(annotation),
    }


@register_tool("CodingVariantFractionTool")
class CodingVariantFractionTool(BaseTool):
    """Compute fraction of coding variants matching a given SO annotation below a VAF threshold.

    CODING allowlist (denominator): synonymous_variant, missense_variant,
    splice_region_variant, stop_gained, stop_lost, start_lost,
    frameshift_variant, inframe_insertion, inframe_deletion. Intronic,
    UTR, intergenic, and up/downstream records are excluded.
    """

    def __init__(self, tool_config: Dict[str, Any], **kwargs):
        super().__init__(tool_config)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        file_path = arguments.get("file", "")
        vaf_threshold = float(arguments.get("vaf_threshold", 0.3))
        annotation = arguments.get("annotation", "synonymous_variant")
        header_rows = int(arguments.get("header_rows", 1))
        vaf_col = arguments.get("vaf_col", "") or ""
        so_col = arguments.get("so_col", "") or ""

        if not file_path or not os.path.exists(file_path):
            return {"status": "error", "error": f"File not found: {file_path}"}
        if header_rows not in (1, 2):
            return {
                "status": "error",
                "error": f"header_rows must be 1 or 2, got {header_rows}",
            }

        try:
            result = compute_variant_fraction(
                file_path=file_path,
                vaf_threshold=vaf_threshold,
                annotation=annotation,
                header_rows=header_rows,
                vaf_col=vaf_col,
                so_col=so_col,
            )
        except ValueError as exc:
            return {"status": "error", "error": str(exc)}
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "error": f"Variant fraction failed: {exc}"}

        return {"status": "success", "data": result}
