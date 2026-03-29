"""
DataQualityTool — pure-Python data quality assessment using pandas.

No external API calls. Reads CSV files or JSON arrays and returns
per-column statistics, overall summary, and quality warnings.
"""

import math
from pathlib import Path
from typing import Any, Dict, List

from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("DataQualityTool")
class DataQualityTool(BaseTool):
    """Assess tabular data quality: missing values, outliers, correlations."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return self._assess(arguments)
        except Exception as e:
            return {"status": "error", "error": f"DataQuality assessment failed: {e}"}

    def _assess(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        import pandas as pd

        data = arguments.get("data")
        if data is None:
            return {"status": "error", "error": "Parameter 'data' is required."}

        # Load data
        if isinstance(data, str):
            path = Path(data)
            if not path.exists():
                return {"status": "error", "error": f"File not found: {data}"}
            df = pd.read_csv(path)
        elif isinstance(data, list):
            if not data:
                return {"status": "error", "error": "Data array is empty."}
            df = pd.DataFrame(data)
        else:
            return {
                "status": "error",
                "error": "Parameter 'data' must be a JSON array of records or a CSV file path.",
            }

        # Filter columns if requested
        col_filter = arguments.get("columns")
        if col_filter:
            missing_cols = [c for c in col_filter if c not in df.columns]
            if missing_cols:
                return {
                    "status": "error",
                    "error": f"Columns not found in data: {missing_cols}",
                }
            df = df[col_filter]

        total_rows = len(df)
        total_cols = len(df.columns)
        complete_cases = int(df.dropna().shape[0])
        complete_pct = (
            round(complete_cases / total_rows * 100, 2) if total_rows else 0.0
        )

        # Per-column stats
        col_stats = {}
        numeric_cols = []
        for col in df.columns:
            series = df[col]
            info: Dict[str, Any] = {
                "dtype": str(series.dtype),
                "missing_count": int(series.isna().sum()),
                "missing_pct": round(float(series.isna().mean()) * 100, 2),
                "unique_values": int(series.nunique(dropna=True)),
            }

            if pd.api.types.is_numeric_dtype(series):
                valid = series.dropna()
                if len(valid) > 0:
                    info["min"] = _safe_float(valid.min())
                    info["max"] = _safe_float(valid.max())
                    info["mean"] = _safe_float(valid.mean())
                    info["std"] = _safe_float(valid.std())
                    info["median"] = _safe_float(valid.median())
                    numeric_cols.append(col)
                else:
                    info["min"] = info["max"] = info["mean"] = info["std"] = info[
                        "median"
                    ] = None
            else:
                valid = series.dropna()
                if len(valid) > 0:
                    mode_val = valid.mode()
                    info["mode"] = str(mode_val.iloc[0]) if len(mode_val) > 0 else None
                    top_vals = valid.value_counts().head(5)
                    info["top_values"] = {str(k): int(v) for k, v in top_vals.items()}
                else:
                    info["mode"] = None
                    info["top_values"] = {}

            col_stats[col] = info

        # Warnings
        warnings: List[Dict[str, str]] = []

        # High missing
        for col, stats in col_stats.items():
            if stats["missing_pct"] > 20:
                warnings.append(
                    {
                        "type": "high_missing",
                        "column": col,
                        "detail": f"{stats['missing_pct']}% missing ({stats['missing_count']}/{total_rows} rows)",
                    }
                )

        # Zero variance
        for col in numeric_cols:
            std = col_stats[col].get("std")
            if std is not None and std == 0:
                warnings.append(
                    {
                        "type": "zero_variance",
                        "column": col,
                        "detail": f"All non-missing values are identical ({col_stats[col]['min']})",
                    }
                )

        # Outliers (>3 SD from mean)
        for col in numeric_cols:
            stats = col_stats[col]
            if stats["std"] is not None and stats["std"] > 0:
                series = df[col].dropna()
                mean, std = stats["mean"], stats["std"]
                outliers = series[(series - mean).abs() > 3 * std]
                if len(outliers) > 0:
                    warnings.append(
                        {
                            "type": "potential_outliers",
                            "column": col,
                            "detail": f"{len(outliers)} value(s) beyond 3 SD from mean: {sorted(outliers.tolist())[:5]}",
                        }
                    )

        # High correlation
        if len(numeric_cols) >= 2:
            corr_matrix = df[numeric_cols].corr()
            seen = set()
            for i, c1 in enumerate(numeric_cols):
                for j, c2 in enumerate(numeric_cols):
                    if i >= j:
                        continue
                    pair = (c1, c2)
                    if pair in seen:
                        continue
                    r = corr_matrix.loc[c1, c2]
                    if not math.isnan(r) and abs(r) > 0.95:
                        seen.add(pair)
                        warnings.append(
                            {
                                "type": "high_correlation",
                                "column": f"{c1}, {c2}",
                                "detail": f"Pearson r = {round(r, 4)}",
                            }
                        )

        return {
            "status": "success",
            "data": {
                "overall": {
                    "total_rows": total_rows,
                    "total_columns": total_cols,
                    "complete_cases": complete_cases,
                    "complete_case_pct": complete_pct,
                },
                "columns": col_stats,
                "warnings": warnings,
            },
        }


def _safe_float(val: Any) -> float | None:
    """Convert to float, returning None for non-finite values."""
    try:
        f = float(val)
        return round(f, 6) if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None
