#!/usr/bin/env python3
"""Compare quadratic / cubic / natural-spline regression models on the same x,y.

For questions like "What is the maximum predicted y at the optimal x according
to the BEST-fitting model among quadratic, cubic and natural spline?":

- Fit `lm(y ~ poly(x, 2, raw = TRUE))`
- Fit `lm(y ~ poly(x, 3, raw = TRUE))`
- Fit `lm(y ~ ns(x, df = K))`     (default K = 4)

For each model, emit R^2, adjusted R^2, F-stat + overall p-value, AIC, BIC,
and the predicted maximum (peak) on a 1000-point grid within the data range,
together with its 95% confidence interval (predict.lm interval='confidence').

Selection rule: highest **adjusted R^2** wins. Also reports AIC / BIC ranking
since they can disagree with R^2 when complexity differs.

All R work runs via Rscript so `splines::ns()` matches what canonical R
notebooks compute. Python `patsy.cr()` does NOT match — see
r_natural_spline_regression.py for details.

CLI
---
python spline_model_compare.py \
    --csv data.csv --y-col Area \
    [--ratio-col Ratio --new-x-col Frequency_rhlI \
       --filter "StrainNumber not in ['1','98']"] \
    [--ns-df 4] [--workdir /tmp/spline_cmp] [--grid-rows 30]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd


SAFE_EXIT_MSG = (
    "Refusing to write inside the input data folder.\n"
    "Pass --workdir <path-outside-input>, e.g. --workdir /tmp/spline_cmp."
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
    p.add_argument("--csv", required=True)
    p.add_argument("--y-col", required=True)
    p.add_argument("--x-col", help="predictor column (or use --ratio-col + --new-x-col)")
    p.add_argument("--ns-df", type=int, default=4, help="natural spline df (default 4)")
    p.add_argument("--ratio-col", default=None,
                   help="if set, split column 'a:b' into a/(a+b) -> --new-x-col")
    p.add_argument("--ratio-sep", default=":")
    p.add_argument("--new-x-col", default="Frequency")
    p.add_argument("--filter", default=None,
                   help="pandas df.query() expression applied before fitting")
    p.add_argument("--workdir", default=None)
    p.add_argument("--grid-rows", type=int, default=30,
                   help="rows to print from each prediction grid")
    p.add_argument("--keep-workdir", action="store_true")
    return p.parse_args()


def prepare_workdir(arg: str | None, input_csv: Path) -> Path:
    wd = Path(arg) if arg else Path(tempfile.mkdtemp(prefix="spline_compare_"))
    wd.mkdir(parents=True, exist_ok=True)
    reject_writing_inside_input(wd, input_csv)
    return wd


def split_ratio_column(df, ratio_col, sep, new_col):
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
ns_df      <- as.integer(args[[4]])
output_dir <- args[[5]]
grid_rows  <- as.integer(args[[6]])

dat <- read.csv(input_csv, stringsAsFactors = FALSE)
dat <- dat[!is.na(dat[[y_col]]) & !is.na(dat[[x_col]]), , drop = FALSE]

xrange <- range(dat[[x_col]])
new_grid <- data.frame(seq(xrange[1], xrange[2], length.out = 1000))
names(new_grid) <- x_col

dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

build_model <- function(model_name, formula_str) {
    fit <- lm(as.formula(formula_str), data = dat)
    s   <- summary(fit)
    fst <- s$fstatistic
    overall_p <- pf(fst[["value"]], fst[["numdf"]], fst[["dendf"]], lower.tail = FALSE)
    pred <- predict(fit, newdata = new_grid, interval = "confidence")
    pred_df <- data.frame(
        x = new_grid[[x_col]],
        fit = pred[, "fit"],
        lwr = pred[, "lwr"],
        upr = pred[, "upr"]
    )
    peak_idx <- which.max(pred_df$fit)
    list(
        name = model_name,
        formula = formula_str,
        r2 = unname(s$r.squared),
        adj_r2 = unname(s$adj.r.squared),
        f_stat = unname(fst[["value"]]),
        f_df1 = unname(fst[["numdf"]]),
        f_df2 = unname(fst[["dendf"]]),
        overall_p = overall_p,
        residual_se = s$sigma,
        df_residual = fit$df.residual,
        nobs = nobs(fit),
        aic = AIC(fit),
        bic = BIC(fit),
        peak_x = pred_df$x[peak_idx],
        peak_y_fit = pred_df$fit[peak_idx],
        peak_y_lwr = pred_df$lwr[peak_idx],
        peak_y_upr = pred_df$upr[peak_idx],
        coefs = coef(fit),
        pred_df = pred_df
    )
}

models <- list(
    quadratic = build_model("quadratic", sprintf("%s ~ poly(%s, 2, raw = TRUE)", y_col, x_col)),
    cubic     = build_model("cubic",     sprintf("%s ~ poly(%s, 3, raw = TRUE)", y_col, x_col)),
    spline    = build_model("spline",    sprintf("%s ~ ns(%s, df = %d)", y_col, x_col, ns_df))
)

# Per-model scalars file
for (m in models) {
    lines <- c(
        sprintf("MODEL\t%s",            m$name),
        sprintf("FORMULA\t%s",          m$formula),
        sprintf("R_SQUARED\t%.10g",     m$r2),
        sprintf("ADJ_R_SQUARED\t%.10g", m$adj_r2),
        sprintf("F_STAT\t%.10g",        m$f_stat),
        sprintf("F_DF1\t%d",            as.integer(m$f_df1)),
        sprintf("F_DF2\t%d",            as.integer(m$f_df2)),
        sprintf("OVERALL_P_VALUE\t%.10e", m$overall_p),
        sprintf("RESIDUAL_SE\t%.10g",   m$residual_se),
        sprintf("DEGREES_OF_FREEDOM\t%d", as.integer(m$df_residual)),
        sprintf("NOBS\t%d",             as.integer(m$nobs)),
        sprintf("AIC\t%.10g",           m$aic),
        sprintf("BIC\t%.10g",           m$bic),
        sprintf("PEAK_X\t%.10g",        m$peak_x),
        sprintf("PEAK_Y_FIT\t%.10g",    m$peak_y_fit),
        sprintf("PEAK_Y_LOWER_95_CI\t%.10g", m$peak_y_lwr),
        sprintf("PEAK_Y_UPPER_95_CI\t%.10g", m$peak_y_upr)
    )
    writeLines(lines, file.path(output_dir, sprintf("scalars_%s.tsv", m$name)))

    n_grid <- nrow(m$pred_df)
    keep <- unique(round(seq(1, n_grid, length.out = grid_rows)))
    write.table(m$pred_df[keep, , drop = FALSE],
                file = file.path(output_dir, sprintf("grid_%s.tsv", m$name)),
                sep = "\t", quote = FALSE, row.names = FALSE)
}

# Comparison table — sorted by adj_r2 desc
ranked_adj_r2 <- names(sort(sapply(models, function(m) m$adj_r2), decreasing = TRUE))
ranked_aic    <- names(sort(sapply(models, function(m) m$aic), decreasing = FALSE))
ranked_bic    <- names(sort(sapply(models, function(m) m$bic), decreasing = FALSE))
best_model    <- ranked_adj_r2[[1]]

cmp_lines <- c(
    "MODEL\tR2\tADJ_R2\tF\tOVERALL_P\tAIC\tBIC\tPEAK_X\tPEAK_Y\tPEAK_Y_LWR_95\tPEAK_Y_UPR_95"
)
for (m in models) {
    cmp_lines <- c(cmp_lines, paste(
        m$name, sprintf("%.6g", m$r2), sprintf("%.6g", m$adj_r2),
        sprintf("%.6g", m$f_stat), sprintf("%.6e", m$overall_p),
        sprintf("%.6g", m$aic), sprintf("%.6g", m$bic),
        sprintf("%.6g", m$peak_x), sprintf("%.6g", m$peak_y_fit),
        sprintf("%.6g", m$peak_y_lwr), sprintf("%.6g", m$peak_y_upr),
        sep = "\t"))
}
writeLines(cmp_lines, file.path(output_dir, "comparison.tsv"))

ranking_lines <- c(
    sprintf("BEST_BY_ADJ_R2\t%s",  best_model),
    sprintf("RANKING_ADJ_R2\t%s",  paste(ranked_adj_r2, collapse = " > ")),
    sprintf("RANKING_AIC\t%s",     paste(ranked_aic,    collapse = " < ")),
    sprintf("RANKING_BIC\t%s",     paste(ranked_bic,    collapse = " < ")),
    sprintf("BEST_PEAK_X\t%.10g",  models[[best_model]]$peak_x),
    sprintf("BEST_PEAK_Y\t%.10g",  models[[best_model]]$peak_y_fit),
    sprintf("BEST_PEAK_Y_LWR_95\t%.10g", models[[best_model]]$peak_y_lwr),
    sprintf("BEST_PEAK_Y_UPR_95\t%.10g", models[[best_model]]$peak_y_upr)
)
writeLines(ranking_lines, file.path(output_dir, "ranking.tsv"))
"""


def run_r(workdir, prepared_csv, y_col, x_col, ns_df, grid_rows):
    driver_path = workdir / "driver.R"
    driver_path.write_text(R_DRIVER)
    out_dir = workdir / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "Rscript", "--vanilla", str(driver_path),
        str(prepared_csv), y_col, x_col, str(ns_df), str(out_dir), str(grid_rows),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    if proc.returncode != 0:
        sys.stderr.write("R driver failed:\n" + proc.stderr + "\n")
        return proc.returncode
    return 0


def emit(workdir, grid_rows):
    out_dir = workdir / "out"
    print("=== COMPARISON ===")
    print((out_dir / "comparison.tsv").read_text().rstrip())
    print()
    print("=== RANKING ===")
    print((out_dir / "ranking.tsv").read_text().rstrip())
    print()
    for name in ("quadratic", "cubic", "spline"):
        scalars = out_dir / f"scalars_{name}.tsv"
        if not scalars.exists():
            continue
        print(f"=== {name.upper()} SCALARS ===")
        print(scalars.read_text().rstrip())
        print()
        grid = out_dir / f"grid_{name}.tsv"
        if grid.exists():
            print(f"=== {name.upper()} GRID (down-sampled to {grid_rows} from 1000) ===")
            print(grid.read_text().rstrip())
            print()


def main() -> int:
    args = parse_args()
    csv_path = Path(args.csv).resolve()
    if not csv_path.exists():
        sys.stderr.write(f"CSV not found: {csv_path}\n")
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
            sys.stderr.write("Need --x-col or (--ratio-col + --new-x-col).\n")
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
        prepared_csv = workdir / "prepared.csv"
        df.to_csv(prepared_csv, index=False)

        rc = run_r(workdir, prepared_csv, args.y_col, x_col, args.ns_df, args.grid_rows)
        if rc != 0:
            return rc
        emit(workdir, args.grid_rows)
        return 0
    finally:
        if cleanup and workdir.exists():
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
