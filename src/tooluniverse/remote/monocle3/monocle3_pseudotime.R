#!/usr/bin/env Rscript
# Monocle3 pseudotime engine (invoked by monocle3_tool.py).
#
# Reads a work directory containing:
#   expr.mtx     - MatrixMarket genes x cells (raw counts)
#   genes.txt    - one gene symbol per row (expr rownames)
#   cells.txt    - one cell id per row (expr colnames)
#   config.json  - {num_dim, root_cluster, root_cells, max_pseudotime_cells}
#   clusters.txt - (optional) one input cluster label per cell
# Writes output.json = {pseudotime, cell_ids, n_cells, n_unreachable,
#                       monocle_partitions, [cluster_pseudotime]}.

suppressMessages({
  library(Matrix)
  library(monocle3)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
work <- args[1]
cfg <- fromJSON(file.path(work, "config.json"))

expr <- as(readMM(file.path(work, "expr.mtx")), "CsparseMatrix")
genes <- readLines(file.path(work, "genes.txt"))
cells <- readLines(file.path(work, "cells.txt"))
rownames(expr) <- genes
colnames(expr) <- cells

gene_meta <- data.frame(gene_short_name = genes, row.names = genes)
cell_meta <- data.frame(row.names = cells)
clusters_path <- file.path(work, "clusters.txt")
has_clusters <- file.exists(clusters_path)
if (has_clusters) cell_meta$input_cluster <- readLines(clusters_path)

cds <- new_cell_data_set(expr, cell_metadata = cell_meta, gene_metadata = gene_meta)
cds <- preprocess_cds(cds, num_dim = min(cfg$num_dim, ncol(expr) - 1))
cds <- reduce_dimension(cds)
cds <- cluster_cells(cds)
cds <- learn_graph(cds)

# Root selection: explicit cells, else all cells of a named input cluster.
root_cells <- NULL
if (!is.null(cfg$root_cells) && length(cfg$root_cells) > 0) {
  root_cells <- intersect(as.character(cfg$root_cells), cells)
} else if (!is.null(cfg$root_cluster) && nzchar(cfg$root_cluster) && has_clusters) {
  root_cells <- cells[cell_meta$input_cluster == cfg$root_cluster]
}
if (is.null(root_cells) || length(root_cells) == 0) {
  stop("Provide root_cells, or root_cluster together with input cluster labels, to orient pseudotime.")
}

cds <- order_cells(cds, root_cells = root_cells)
pt <- pseudotime(cds)
n_unreachable <- sum(is.infinite(pt))
pt[is.infinite(pt)] <- NA # cells disconnected from the root -> null

result <- list(
  pseudotime = round(as.numeric(pt), 5),
  cell_ids = names(pt),
  n_cells = length(pt),
  n_unreachable = n_unreachable,
  monocle_partitions = as.character(partitions(cds))
)

if (has_clusters) {
  cpt <- tapply(pt, cell_meta$input_cluster, function(x) mean(x, na.rm = TRUE))
  result$cluster_pseudotime <- as.list(round(cpt, 5))
}

max_cells <- if (!is.null(cfg$max_pseudotime_cells)) cfg$max_pseudotime_cells else 50000
if (length(pt) > max_cells) {
  result$pseudotime <- NULL
  result$cell_ids <- NULL
  result$monocle_partitions <- NULL
  result$note <- paste0(length(pt), " cells > ", max_cells,
                        ": per-cell pseudotime omitted; see cluster_pseudotime.")
}

write_json(result, file.path(work, "output.json"), auto_unbox = TRUE, na = "null")
