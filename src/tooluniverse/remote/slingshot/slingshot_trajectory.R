#!/usr/bin/env Rscript
# Slingshot trajectory inference engine (invoked by slingshot_tool.py).
#
# Reads a work directory containing:
#   embedding.csv  - cells x dims reduced embedding (no header)
#   clusters.txt   - one cluster label per cell (same order as embedding rows)
#   config.json    - {start_cluster, end_clusters, max_pseudotime_cells}
# Writes output.json = {lineages, lineage_names, n_lineages,
#                       [pseudotime], cluster_pseudotime}.

suppressMessages({
  library(slingshot)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
work <- args[1]
cfg <- fromJSON(file.path(work, "config.json"))

emb <- as.matrix(read.csv(file.path(work, "embedding.csv"), header = FALSE))
clusters <- readLines(file.path(work, "clusters.txt"))

sl_args <- list(data = emb, clusterLabels = clusters)
if (!is.null(cfg$start_cluster) && nzchar(cfg$start_cluster)) {
  sl_args$start.clus <- cfg$start_cluster
}
if (!is.null(cfg$end_clusters) && length(cfg$end_clusters) > 0) {
  sl_args$end.clus <- as.character(cfg$end_clusters)
}

sds <- do.call(slingshot, sl_args)

# unname() so jsonlite writes a JSON array-of-arrays (ordered cluster sequences),
# not an object keyed by the R list's Lineage1/Lineage2 names.
lineages <- unname(lapply(slingLineages(sds), as.character))
pt <- slingPseudotime(sds) # cells x lineages, NA where cell not on a lineage
lineage_names <- colnames(pt)

# Per-cluster mean pseudotime along each lineage (compact, always returned).
cluster_pt <- list()
for (clu in sort(unique(clusters))) {
  m <- clusters == clu
  cluster_pt[[clu]] <- as.list(colMeans(pt[m, , drop = FALSE], na.rm = TRUE))
}

result <- list(
  lineages = lineages,
  lineage_names = lineage_names,
  n_lineages = length(lineages),
  cluster_pseudotime = cluster_pt
)

max_cells <- if (!is.null(cfg$max_pseudotime_cells)) cfg$max_pseudotime_cells else 50000
if (nrow(pt) <= max_cells) {
  # jsonlite writes NA as null; round for compactness
  result$pseudotime <- round(pt, 4)
} else {
  result$note <- paste0(nrow(pt), " cells > ", max_cells,
                        ": per-cell pseudotime omitted; see cluster_pseudotime.")
}

write_json(result, file.path(work, "output.json"), auto_unbox = TRUE, na = "null")
