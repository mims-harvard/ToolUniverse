#!/usr/bin/env Rscript
# SingleR cell-type annotation engine (invoked by singler_tool.py).
#
# Reads a work directory containing:
#   config.json        - {celldex_ref, ref_label_field}  (reference selection)
#   query.mtx          - MatrixMarket genes x cells (log-normalized)
#   query_genes.txt    - one gene symbol per row (query rownames)
# and, for a bring-your-own reference (celldex_ref empty):
#   ref.mtx, ref_genes.txt, ref_labels.txt  - labeled reference matrix + labels
#
# Writes output.json = {predicted_labels, n_cells, ref, [delta_median]}.

suppressMessages({
  library(Matrix)
  library(SingleR)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
work <- args[1]
cfg <- fromJSON(file.path(work, "config.json"))

read_mtx <- function(prefix) {
  m <- readMM(file.path(work, paste0(prefix, ".mtx")))
  rownames(m) <- readLines(file.path(work, paste0(prefix, "_genes.txt")))
  as(m, "CsparseMatrix")
}

query <- read_mtx("query")

celldex_ref <- cfg$celldex_ref
if (!is.null(celldex_ref) && nzchar(celldex_ref)) {
  suppressMessages(library(celldex))
  ref_fun <- get(celldex_ref, asNamespace("celldex"))
  ref_se <- ref_fun()
  label_field <- if (!is.null(cfg$ref_label_field)) cfg$ref_label_field else "label.main"
  pred <- SingleR(test = query, ref = ref_se, labels = ref_se[[label_field]])
  ref_name <- celldex_ref
} else {
  ref_mat <- read_mtx("ref")
  ref_labels <- readLines(file.path(work, "ref_labels.txt"))
  pred <- SingleR(test = query, ref = ref_mat, labels = ref_labels)
  ref_name <- "user_reference"
}

result <- list(
  predicted_labels = as.character(pred$labels),
  n_cells = ncol(query),
  ref = ref_name
)
write_json(result, file.path(work, "output.json"), auto_unbox = TRUE)
