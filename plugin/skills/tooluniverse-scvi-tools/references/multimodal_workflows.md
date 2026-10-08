# Multi-Modal scvi-tools Workflows: totalVI, MultiVI, DestVI

These three models share a theme -- jointly modeling two data types -- but
each expects a different input shape. Get the input shape right first;
most failures here are data-formatting mistakes, not modeling mistakes.

## totalVI: CITE-seq (RNA + surface protein)

Input: an AnnData with RNA counts in `.layers['counts']` (as usual) AND a
separate protein-count matrix (cells x proteins, e.g. antibody-derived tag
counts) in `.obsm['protein_counts']` (or whatever key you pass to
`--protein-obsm`). The two matrices must share the same cell index/order.

```bash
python prepare_data.py cite_raw.h5ad prepared.h5ad --batch-key batch
python train_model.py prepared.h5ad results/ --model totalvi \
    --protein-obsm protein_counts --batch-key batch
```

Output: `obsm['X_totalvi']` is a joint RNA+protein latent space. totalVI
also denoises the protein counts (removing background/ambient antibody
signal) -- accessible via `model.get_normalized_expression()` on the loaded
model for RNA, or `model.get_protein_foreground_probability()` for
per-protein background estimates (see scvi-tools docs; not wrapped in a
script here since the output format varies by downstream need).

**Common mistake**: passing normalized protein counts instead of raw ADT
counts. totalVI, like every model in this skill, needs raw integer counts
for both modalities.

## MultiVI: multiome (RNA + ATAC, same cells)

Input: a single AnnData with BOTH gene expression and ATAC peak features
concatenated along `var`, distinguished by a `var['modality']` column with
values `"Gene Expression"` and `"Peaks"` (this is the standard output shape
of 10x Genomics multiome Cell Ranger ARC output loaded via
`scanpy.read_10x_h5` on the filtered feature matrix, or `muon`'s
`MuData` flattened to a single AnnData).

```bash
python train_model.py prepared_multiome.h5ad results/ --model multivi --batch-key batch
```

`train_model.py` infers `n_genes` from `var['modality'] == "Gene Expression"`
and treats every remaining feature as a peak region (`n_regions`). If your
data lacks a `modality` column, add it before calling `prepare_data.py` --
do not guess the gene/peak split by feature name pattern, since that is
technology-specific and easy to get wrong silently.

MultiVI can also train on RNA-only or ATAC-only cells mixed with
paired cells (semi-paired multiome) -- see scvi-tools' own MultiVI tutorial
for that setup; the modality column convention is the same.

## DestVI: spatial deconvolution (two-stage, not a single train_model.py call)

DestVI needs TWO fits, not one, because it first learns cell-type-specific
expression profiles from a labeled single-cell reference, then uses those
profiles to decompose each spatial spot into a mixture of cell types.
`train_model.py` does not cover this two-stage pattern; run it directly:

```python
import scvi
from scvi.model import CondSCVI, DestVI

# Stage 1: fit CondSCVI on the labeled single-cell reference
CondSCVI.setup_anndata(sc_adata, layer="counts", labels_key="cell_type")
sc_model = CondSCVI(sc_adata, weight_obs=False)
sc_model.train(max_epochs=200)

# Stage 2: fit DestVI on the spatial data using the reference's cell-type
# profiles
DestVI.setup_anndata(spatial_adata, layer="counts")
spatial_model = DestVI.from_rna_model(spatial_adata, sc_model)
spatial_model.train(max_epochs=2500)

proportions = spatial_model.get_proportions()  # spots x cell types
```

**Prerequisite check before running this**: the single-cell reference's
`cell_type` labels must be reasonably clean (run scANVI or manual annotation
first if the reference is unlabeled) -- DestVI's deconvolution is only as
good as the reference profiles it is built from.

## Cross-reference

For plain scRNA-seq QC before any of the above (mito%, doublets, ambient
RNA), always run `tooluniverse-single-cell`'s QC pass first -- none of these
three models perform QC internally, and training on un-QC'd data (empty
droplets, doublets) produces cell-type profiles contaminated by technical
artifacts.
