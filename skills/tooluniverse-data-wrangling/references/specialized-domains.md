# Specialized Domain API Patterns

Additional API patterns for domains beyond the core 10 in SKILL.md. Each shows which ToolUniverse tools exist and how to go beyond them with direct API calls.

## Table of Contents
- [11. Proteomics](#11-proteomics)
- [12. Metabolomics](#12-metabolomics)
- [13. Microbiome](#13-microbiome)
- [14. Ecology & Biodiversity](#14-ecology)
- [15. Model Organisms](#15-model-organisms)
- [16. Pathways & Networks](#16-pathways)
- [17. Ontologies](#17-ontologies)
- [18. Immunology](#18-immunology)
- [19. Drug & Pharmacology](#19-drug-pharmacology)
- [20. Imaging & Atlases](#20-imaging)
- [21. Protein Structure Download](#21-protein-structure)
- [22. Clinical Genomics & Variants](#22-clinical-genomics)
- [23. Single-Cell Portals](#23-single-cell)
- [24. Toxicology & Environmental](#24-toxicology)

---

### 11. Proteomics (PRIDE, MassIVE, PeptideAtlas, ProteomeXchange) {#11-proteomics}
Tools: `PRIDE_*`, `MassIVE_*`, `PeptideAtlas_*`
```python
# PRIDE project files — search then download raw/processed data
project = requests.get("https://www.ebi.ac.uk/pride/ws/archive/v2/projects/PXD012345").json()
files = requests.get(f"https://www.ebi.ac.uk/pride/ws/archive/v2/projects/PXD012345/files").json()
for f in files:
    if f["fileName"].endswith(".mzML"):  # mass spec data
        download_url = f["publicFileLocations"][0]["value"]

# ProteomeXchange: search across PRIDE + MassIVE + jPOST
px = requests.get("https://proteomecentral.proteomexchange.org/cgi/GetDataset?ID=PXD012345&outputMode=JSON").json()
```

### 12. Metabolomics (MetaboLights, Metabolomics Workbench, HMDB) {#12-metabolomics}
Tools: `MetaboLights_*`, `MetabolomicsWorkbench_*`, `HMDB_*`
```python
# MetaboLights study download
study_id = "MTBLS1234"
study = requests.get(f"https://www.ebi.ac.uk/metabolights/ws/studies/{study_id}").json()
# Download metabolite assignment file
files = requests.get(f"https://www.ebi.ac.uk/metabolights/ws/studies/{study_id}/files").json()

# Metabolomics Workbench REST
mw = requests.get("https://www.metabolomicsworkbench.org/rest/study/study_id/ST001234/analysis").json()

# HMDB metabolite data
hmdb = requests.get("https://hmdb.ca/metabolites/HMDB0000001.xml").text  # XML format
```

### 13. Microbiome & Metagenomics (MGnify, GMREPO) {#13-microbiome}
Tools: `MGnify_*`, `GMREPO_*`
```python
# MGnify: search analyses, download taxonomy/function profiles
analyses = requests.get("https://www.ebi.ac.uk/metagenomics/api/v1/analyses",
    params={"study_accession": "MGYS00001234", "page_size": 100}).json()
# Download OTU/taxonomy TSV
for a in analyses["data"]:
    tax_url = f"https://www.ebi.ac.uk/metagenomics/api/v1/analyses/{a['id']}/downloads"
    downloads = requests.get(tax_url).json()

# GMREPO: gut microbiome phenotype associations
gmrepo = requests.get("https://gmrepo.humangut.info/api/getAssociatedSpeciesByMeshID",
    params={"meshID": "D003920"}).json()  # diabetes
```

### 14. Ecology & Biodiversity (GBIF, iNaturalist, OBIS) {#14-ecology}
Tools: `GBIF_*`, `iNaturalist_*`, `OBIS_*`
```python
# GBIF occurrence data (millions of records, paginated)
all_records = []
offset = 0
while True:
    resp = requests.get("https://api.gbif.org/v1/occurrence/search",
        params={"scientificName": "Panthera tigris", "limit": 300, "offset": offset}).json()
    all_records.extend(resp["results"])
    if resp["endOfRecords"]: break
    offset += 300

# iNaturalist observations
obs = requests.get("https://api.inaturalist.org/v1/observations",
    params={"taxon_name": "Danaus plexippus", "per_page": 200, "geo": "true"}).json()
```

### 15. Model Organisms (FlyBase, WormBase, ZFIN, RGD, MGI) {#15-model-organisms}
Tools: `FlyBase_*`, `WormBase_*`, `ZFIN_*`, `RGD_*`
```python
# FlyBase gene data
fb = requests.get("https://api.flybase.org/api/v1.0/gene/FBgn0000490").json()  # dpp gene

# WormBase gene info
wb = requests.get("https://wormbase.org/rest/widget/gene/WBGene00006763/overview",
    headers={"Accept": "application/json"}).json()

# ZFIN (zebrafish) gene expression
zfin = requests.get("https://zfin.org/action/api/marker/ZDB-GENE-980526-166/expression").json()

# RGD (rat) — disease annotations for a gene
rgd = requests.get("https://rest.rgd.mcw.edu/rgdws/genes/Tp53/9606").json()  # human TP53
```

### 16. Pathways & Networks (Reactome, STRING, BioGRID, WikiPathways) {#16-pathways}
Tools: `Reactome_*`, `STRING_*`, `BioGRID_*`, `WikiPathways_*`
```python
# Reactome pathway participants
pathway_id = "R-HSA-109582"  # Hemostasis
participants = requests.get(f"https://reactome.org/ContentService/data/participants/{pathway_id}").json()

# STRING protein-protein interactions (bulk)
proteins = "9606.ENSP00000269305%0d9606.ENSP00000344818"  # TP53, MDM2
network = requests.get(f"https://string-db.org/api/json/network?identifiers={proteins}&species=9606").json()

# BioGRID interactions for a gene (tab-delimited bulk)
url = "https://webservice.thebiogrid.org/interactions/?searchNames=true&geneList=BRCA1&taxId=9606&format=json&accesskey=YOUR_KEY"

# WikiPathways: download pathway as GPML or GMT
gpml = requests.get("https://www.wikipathways.org/wikipathways/wpi/wpi.php?action=downloadFile&type=gpml&pwTitle=Pathway:WP254").text
```

### 17. Ontologies (OLS, Gene Ontology, HPO, Disease Ontology) {#17-ontologies}
Tools: `ols_search_terms`, `ols_get_term_info`, `Gene_Ontology_*`
```python
# OLS term search + hierarchy traversal
terms = requests.get("https://www.ebi.ac.uk/ols4/api/search",
    params={"q": "apoptosis", "ontology": "go", "rows": 20}).json()

# Get children of a GO term
children = requests.get("https://www.ebi.ac.uk/ols4/api/ontologies/go/terms/http%253A%252F%252Fpurl.obolibrary.org%252Fobo%252FGO_0006915/children").json()

# HPO: phenotype-to-disease annotations
hpo = requests.get("https://hpo.jax.org/api/hpo/term/HP:0001250/diseases").json()

# Gene Ontology annotations bulk (GAF format)
# Download from: http://current.geneontology.org/annotations/goa_human.gaf.gz
```

### 18. Immunology (IEDB, VDJdb, ImmPort) {#18-immunology}
Tools: `IEDB_*`, `VDJdb_*`
```python
# IEDB epitope search
epitopes = requests.get("https://query-api.iedb.org/epitope_search",
    params={"linear_sequence": "SIINFEKL", "limit": 50}).json()

# VDJdb: T-cell receptor specificity database
vdjdb = pd.read_csv("https://raw.githubusercontent.com/antigenomics/vdjdb-db/master/latest-version.zip",
    compression="zip", sep="\t")

# ImmPort shared data (requires registration)
# Search at: https://www.immport.org/shared/search
```

### 19. Drug & Pharmacology (DrugBank, PharmGKB, SIDER, DGIdb) {#19-drug-pharmacology}
Tools: `PharmGKB_*`, `DGIdb_*`, `SIDER_*`, `DrugCentral_*`
```python
# DGIdb drug-gene interactions
dgi = requests.get("https://dgidb.org/api/v2/interactions.json",
    params={"genes": "EGFR", "interaction_sources": "DrugBank,ChEMBL"}).json()

# PharmGKB clinical annotations for a gene
pgkb = requests.get("https://api.pharmgkb.org/v1/data/clinicalAnnotation",
    params={"view": "base", "location.genes.symbol": "CYP2D6"}).json()

# SIDER side effect frequencies (bulk download)
# Download from: http://sideeffects.embl.de/media/download/meddra_freq.tsv.gz
```

### 20. Imaging & Atlases (TCIA, HPA, Allen Brain Atlas, BioImage Archive) {#20-imaging}
Tools: `TCIA_*`, `HPA_*`, `AllenBrainAtlas_*`
```python
# TCIA: cancer imaging collections
collections = requests.get("https://services.cancerimagingarchive.net/nbia-api/services/v1/getCollectionValues").json()
# Get series for a patient
series = requests.get("https://services.cancerimagingarchive.net/nbia-api/services/v1/getSeries",
    params={"Collection": "TCGA-BRCA", "PatientID": "TCGA-A1-A0SB"}).json()

# Human Protein Atlas: tissue expression
hpa = requests.get("https://www.proteinatlas.org/api/search_download.php?search=TP53&format=json&columns=g,t,up").json()

# Allen Brain Atlas: gene expression in brain regions
aba = requests.get("https://api.brain-map.org/api/v2/data/query.json?criteria=model::Gene,rma::criteria,[acronym$eq'BDNF']").json()
```

### 21. Protein Structure Download (RCSB PDB, AlphaFold, CATH) {#21-protein-structure}
Tools: `RCSB_*`, `AlphaFold_*`, `PDBe_*`, `CATH_*`
```python
# Download PDB/CIF structure files directly
pdb_id = "1A2B"
pdb_content = requests.get(f"https://files.rcsb.org/download/{pdb_id}.pdb").text
cif_content = requests.get(f"https://files.rcsb.org/download/{pdb_id}.cif").text

# AlphaFold predicted structure by UniProt ID
uniprot_id = "P04637"  # TP53
af_pdb = requests.get(f"https://alphafold.ebi.ac.uk/files/AF-{uniprot_id}-F1-model_v4.pdb").text
af_cif = requests.get(f"https://alphafold.ebi.ac.uk/files/AF-{uniprot_id}-F1-model_v4.cif").text

# RCSB advanced search (GraphQL) for bulk queries
query = {"query": {"type": "terminal", "service": "text", "parameters": {"attribute": "rcsb_entity_source_organism.taxonomy_lineage.name", "operator": "exact_match", "value": "Homo sapiens"}}, "return_type": "entry", "request_options": {"paginate": {"start": 0, "rows": 100}}}
results = requests.post("https://search.rcsb.org/rcsbsearch/v2/query", json=query).json()
```

### 22. Clinical Genomics & Variant Databases (ClinVar, ClinGen, CIViC, OncoKB) {#22-clinical-genomics}
Tools: `ClinVar_*`, `ClinGen_*`, `CIViC_*`, `OncoKB_*`
```python
# ClinVar bulk download (variant_summary, ~200MB)
# df = pd.read_csv("https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz", sep="\t")

# CIViC GraphQL API — all evidence items for a gene
query = '{"query": "{ gene(entrezId: 673) { name variants { nodes { name evidenceItems { nodes { description evidenceLevel } } } } } }"}'
civic = requests.post("https://civicdb.org/api/graphql", json={"query": query}).json()

# ClinGen allele registry
allele = requests.get("https://reg.clinicalgenome.org/allele?hgvs=NM_000059.4:c.68_69del").json()
```

### 23. Single-Cell Portals (cellxgene, ARCHS4, Cell Marker) {#23-single-cell}
Tools: `cellxgene_*`, `ARCHS4_*`
```python
# cellxgene Census — query human single-cell data at scale
import cellxgene_census  # requires cellxgene-census
census = cellxgene_census.open_soma()
adata = cellxgene_census.get_anndata(census, organism="Homo sapiens",
    obs_value_filter="tissue_general == 'lung' and disease == 'normal'")

# ARCHS4 gene expression (pre-computed from SRA)
archs4 = requests.get("https://maayanlab.cloud/archs4/search/loadExpressionTSV.php",
    params={"search": "BRCA1", "species": "human"}).text

# Without cellxgene_census: download h5ad directly from cellxgene data portal
# Browse collections at https://cellxgene.cziscience.com/collections
```

### 24. Toxicology & Environmental (CTD, EPA, Tox21) {#24-toxicology}
Tools: `CTD_*`, `EPA_*`
```python
# CTD: chemical-gene-disease interactions
ctd = requests.get("https://ctdbase.org/tools/batchQuery.go",
    params={"inputType": "chem", "inputTerms": "Bisphenol A", "report": "genes_curated", "format": "json"}).json()

# EPA CompTox Dashboard
comptox = requests.get("https://comptox.epa.gov/dashboard/api/search/chemical/equal/Bisphenol%20A").json()
```
