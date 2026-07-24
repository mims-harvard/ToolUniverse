#!/usr/bin/env python3
"""Run a natural-spline regression `lm(y ~ ns(x, df=K))` in R via Rscript.

R's `splines::ns(x, df=K)` and Python `patsy.dmatrix("cr(x, df=K)")` produce
DIFFERENT design matrices because of internal-knot placement, boundary-knot
placement, and basis orthogonalization. For any question that references R
syntax (`lm(... ns(x, df=4))`), this script is the deterministic answer.

It emits:

    R_SQUARED            <float, multiple R^2>
    ADJ_R_SQUARED        <float>
    F_STAT               <float, overall F>
    F_DF1 / F_DF2        <int, df>
    OVERALL_P_VALUE      <float, F-test p>
    RESIDUAL_SE          <float>
    DEGREES_OF_FREEDOM   <int>
    NOBS                 <int>

    PEAK_X               <float, x at maximum predicted y on a 1000-point grid>
    PEAK_Y_FIT           <float, predicted y at peak>
    PEAK_Y_LOWER_95_CI   <float, predict.lm(..., interval='confidence')[, 'lwr']>
    PEAK_Y_UPPER_95_CI   <float, predict.lm(..., interval='confidence')[, 'upr']>

    COEFFICIENTS         <name, estimate, std_error, t_value, p_value> table
    GRID_PREDICTIONS     <x, fit, lwr, upr> small CSV (50 rows by default)

Workspace isolation
-------------------
The script writes its R driver to --workdir (defaults to /tmp/<tmpdir>).
It refuses to write into the input data folder — input data must stay
untouched so re-runs are reproducible.

CLI
---
python r_natural_spline_regression.py \
    --csv Swarm.csv \
    --y-col Area \
    --x-col Frequency \
    --df 4 \
    [--filter "StrainNumber not in (1, 98)"] \
    [--ratio-col Ratio --ratio-sep ":" --new-x-col Frequency_rhlI] \
    [--workdir /tmp/spline_run] \
    [--grid-rows 50]

Filter syntax: a pandas `df.query()` string evaluated AFTER ratio expansion
but BEFORE the regression. Use this to drop pure-strain rows, e.g.
``--filter "StrainNumber not in (1, 98)"``.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd


SAFE_EXIT_MSG = (
    "Refusing to write inside the input data folder.\n"
    "Pass --workdir <path-outside-input>, e.g. --workdir /tmp/spline_run."
)


def reject_writing_inside_input(workdir: Path, input_csv: Path) -> None:
    """Refuse to write into the directory holding the input CSV (or any
    ancestor of it). Input data must remain untouched for reproducibility."""
    workdir_r = workdir.resolve()
    input_dir = input_csv.resolve().parent
    if workdir_r == input_dir or input_dir in workdir_r.parents:
        sys.stderr.write(SAFE_EXIT_MSG + f"\nOffending workdir: {workdir}\n")
        sys.exit(2)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--csv", required=True, help="input CSV path (read-only)")
    p.add_argument("--y-col", required=True, help="response column")
    p.add_argument("--x-col", help="predictor column (or use --ratio-col + --new-x-col)")
    p.add_argument("--df", type=int, default=4, help="natural spline degrees of freedom (default 4)")
    p.add_argument("--filter", default=None,
                   help="pandas df.query() expression applied before fitting "
                        "(e.g. \"StrainNumber not in (1, 98)\")")
    p.add_argument("--ratio-col", default=None,
                   help="if set, split column 'a:b' into two integers and compute frequency = a/(a+b)")
    p.add_argument("--ratio-sep", default=":", help="separator for --ratio-col (default ':')")
    p.add_argument("--new-x-col", default="Frequency",
                   help="name of derived frequency column when using --ratio-col")
    p.add_argument("--workdir", default=None,
                   help="writable scratch directory (default /tmp/<auto>); never write into the input data folder")
    p.add_argument("--grid-rows", type=int, default=50,
                   help="rows to print from the prediction grid (default 50)")
    p.add_argument("--keep-workdir", action="store_true",
                   help="don't remove --workdir on exit (debugging)")
    return p.parse_args()


def prepare_workdir(arg: str | None, input_csv: Path) -> Path:
    if arg:
        wd = Path(arg)
    else:
        wd = Path(tempfile.mkdtemp(prefix="r_ns_regression_"))
    wd.mkdir(parents=True, exist_ok=True)
    reject_writing_inside_input(wd, input_csv)
    return wd


def split_ratio_column(df: pd.DataFrame, ratio_col: str, sep: str, new_col: str) -> pd.DataFrame:
    """Convert "a:b" string ratios -> frequency = a / (a+b)."""
    if ratio_col not in df.columns:
        sys.stderr.write(f"--ratio-col {ratio_col!r} not in CSV columns: {list(df.columns)}\n")
        sys.exit(2)

    parts = df[ratio_col].astype(str).str.split(sep, n=1, expand=True)
    a = pd.to_numeric(parts[0], errors="coerce")
    b = pd.to_numeric(parts[1], errors="coerce")
    df[new_col] = a / (a + b)
    return df


R_DRIVER = r"""
suppressPackageStartupMessages({
    library(splines)
})

args <- commandArgs(trailingOnly = TRUE)
input_csv  <- args[[1]]
y_col      <- args[[2]]
x_col      <- args[[3]]
df_value   <- as.integer(args[[4]])
output_dir <- args[[5]]
grid_rows  <- as.integer(args[[6]])

dat <- read.csv(input_csv, stringsAsFactors = FALSE)

if (!(y_col %in% names(dat))) stop(sprintf("y column '%s' missing", y_col))
if (!(x_col %in% names(dat))) stop(sprintf("x column '%s' missing", x_col))

dat <- dat[!is.na(dat[[y_col]]) & !is.na(dat[[x_col]]), , drop = FALSE]

formula <- as.formula(sprintf("%s ~ ns(%s, df = %d)", y_col, x_col, df_value))
fit <- lm(formula, data = dat)
fit_summary <- summary(fit)

# Overall model F-test
fstat <- fit_summary$fstatistic
overall_p <- pf(fstat[["value"]], fstat[["numdf"]], fstat[["dendf"]], lower.tail = FALSE)

# Coefficient table
coefs <- as.data.frame(fit_summary$coefficients)
coefs <- cbind(name = rownames(coefs), coefs)
rownames(coefs) <- NULL
names(coefs) <- c("name", "estimate", "std_error", "t_value", "p_value")

# Prediction grid (1000 points) for peak detection
xrange <- range(dat[[x_col]])
new_grid <- data.frame(seq(xrange[1], xrange[2], length.out = 1000))
names(new_grid) <- x_col
pred <- predict(fit, newdata = new_grid, interval = "confidence")
pred_df <- data.frame(
    x = new_grid[[x_col]],
    fit = pred[, "fit"],
    lwr = pred[, "lwr"],
    upr = pred[, "upr"]
)
peak_idx <- which.max(pred_df$fit)

scalars <- list(
    R_SQUARED          = unname(fit_summary$r.squared),
    ADJ_R_SQUARED      = unname(fit_summary$adj.r.squared),
    F_STAT             = unname(fstat[["value"]]),
    F_DF1              = unname(fstat[["numdf"]]),
    F_DF2              = unname(fstat[["dendf"]]),
    OVERALL_P_VALUE    = overall_p,
    RESIDUAL_SE        = fit_summary$sigma,
    DEGREES_OF_FREEDOM = fit$df.residual,
    NOBS               = nobs(fit),
    PEAK_X             = pred_df$x[peak_idx],
    PEAK_Y_FIT         = pred_df$fit[peak_idx],
    PEAK_Y_LOWER_95_CI = pred_df$lwr[peak_idx],
    PEAK_Y_UPPER_95_CI = pred_df$upr[peak_idx]
)

# Write outputs
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

scalar_lines <- vapply(names(scalars), function(k) {
    v <- scalars[[k]]
    if (is.numeric(v) && !is.na(v) && abs(v) > 0 && abs(v) < 1e-3) {
        sprintf("%s\t%.10e", k, v)
    } else {
        sprintf("%s\t%.10g", k, v)
    }
}, character(1))
writeLines(scalar_lines, file.path(output_dir, "scalars.tsv"))

write.table(coefs, file = file.path(output_dir, "coefficients.tsv"),
            sep = "\t", quote = FALSE, row.names = FALSE)

# Down-sample the prediction grid to grid_rows for printing
n_grid <- nrow(pred_df)
keep <- unique(round(seq(1, n_grid, length.out = grid_rows)))
write.table(pred_df[keep, , drop = FALSE],
            file = file.path(output_dir, "grid_predictions.tsv"),
            sep = "\t", quote = FALSE, row.names = FALSE)
"""


def run_r(workdir: Path, prepared_csv: Path, y_col: str, x_col: str, df_value: int, grid_rows: int) -> int:
    driver_path = workdir / "driver.R"
    driver_path.write_text(R_DRIVER)
    out_dir = workdir / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "Rscript", "--vanilla", str(driver_path),
        str(prepared_csv), y_col, x_col, str(df_value), str(out_dir), str(grid_rows),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    if proc.returncode != 0:
        sys.stderr.write("R driver failed:\n" + proc.stderr + "\n")
        return proc.returncode
    return 0


def emit(workdir: Path, grid_rows: int) -> None:
    out_dir = workdir / "out"
    scalars_path = out_dir / "scalars.tsv"
    coefs_path = out_dir / "coefficients.tsv"
    grid_path = out_dir / "grid_predictions.tsv"

    if not scalars_path.exists():
        sys.stderr.write("R driver did not produce scalars.tsv\n")
        sys.exit(3)

    print("=== SCALARS ===")
    print(scalars_path.read_text().rstrip())
    print()
    print("=== COEFFICIENTS ===")
    print(coefs_path.read_text().rstrip())
    print()
    print(f"=== PREDICTION GRID (down-sampled to {grid_rows} rows from 1000) ===")
    print(grid_path.read_text().rstrip())


def main() -> int:
    args = parse_args()

    csv_path = Path(args.csv).resolve()
    if not csv_path.exists():
        sys.stderr.write(f"Input CSV not found: {csv_path}\n")
        return 2

    workdir = prepare_workdir(args.workdir, csv_path)
    cleanup = (not args.keep_workdir) and (args.workdir is None)

    try:
        df = pd.read_csv(csv_path)

        if args.ratio_col:
            df = split_ratio_column(df, args.ratio_col, args.ratio_sep, args.new_x_col)
            x_col = args.new_x_col
        elif args.x_col:
            x_col = args.x_col
        else:
            sys.stderr.write("Either --x-col or (--ratio-col + --new-x-col) is required.\n")
            return 2

        if args.filter:
            before = len(df)
            try:
                df = df.query(args.filter)
            except Exception as exc:
                sys.stderr.write(f"--filter failed: {exc}\n")
                return 2
            sys.stderr.write(f"# filter: kept {len(df)}/{before} rows after `{args.filter}`\n")

        df = df.dropna(subset=[args.y_col, x_col])
        if len(df) < (args.df + 2):
            sys.stderr.write(f"Too few rows ({len(df)}) for df={args.df}\n")
            return 2

        prepared_csv = workdir / "prepared.csv"
        df.to_csv(prepared_csv, index=False)

        rc = run_r(workdir, prepared_csv, args.y_col, x_col, args.df, args.grid_rows)
        if rc != 0:
            return rc

        emit(workdir, args.grid_rows)
        return 0
    finally:
        if cleanup and workdir.exists():
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
