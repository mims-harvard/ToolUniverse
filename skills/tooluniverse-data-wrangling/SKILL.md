---
name: tooluniverse-data-wrangling
description: Universal data access reference for scientific research. Teaches how to download bulk data, parse any scientific file format (VCF, h5ad, mzML, PDB, FASTA, XPT, NIfTI, and 30+ more), paginate REST APIs, and handle authentication. Covers 24 domain API patterns across ALL life science data sources — genomics, proteomics, clinical, imaging, ecology, and more. Use this skill whenever you need to download raw data, parse a file format, access a bulk API, write a multi-step data retrieval workflow, or when a ToolUniverse tool returns metadata but you need the actual data. Also use when the data source has no ToolUniverse tool at all. Even if the user doesn't say "data wrangling" — if their task requires getting data from a scientific database or parsing a scientific file format, this is the skill to use.
---

# Data Wrangling: Universal Access Patterns

Reference for downloading and parsing scientific data from any source. Write and run Python code via Bash for every step.

## When to Use

- ToolUniverse tool returned metadata/search results but you need **raw or bulk data**
- Data is in a format tools don't parse (VCF, h5ad, BAM, SDF, GCT)
- You need a **multi-step API workflow** (search -> filter -> download -> parse)
- The data source has **no ToolUniverse tool** at all
- You need **thousands of records**, not the 10-100 a tool returns

## Decision: Tool vs Code

| Situation | Use |
|-----------|-----|
| Single record lookup, simple search, <100 results | ToolUniverse tool (`execute_tool`) |
| Bulk download, custom filtering, format conversion | Write Python code |
| Tool exists but returns truncated results | Write code using the same API the tool wraps |
| No tool exists for this source | Write code directly |

---

## Section A: Format Cookbook

### Tabular
```python
import pandas as pd, io

df = pd.read_csv("data.csv")                                # CSV
df = pd.read_csv("data.tsv", sep="\t")                      # TSV
df = pd.read_sas(io.BytesIO(content), format="xport")       # SAS Transport (XPT) — NHANES, CDC
df = pd.read_sas("data.sas7bdat", format="sas7bdat")        # SAS native
df = pd.read_stata("data.dta")                               # Stata — ICPSR, HRS
df = pd.read_parquet("data.parquet")                         # Parquet — MIMIC-IV
df = pd.read_excel("data.xlsx")                              # Excel
df = pd.read_spss("data.sav")                                # SPSS
df = pd.read_fwf("data.dat")                                 # Fixed-width — legacy surveys
```

### Genomics
```python
from Bio import SeqIO
records = list(SeqIO.parse("seqs.fasta", "fasta"))           # FASTA
records = list(SeqIO.parse("reads.fastq", "fastq"))          # FASTQ

# VCF (no cyvcf2 needed)
vcf_lines = [l for l in open("vars.vcf") if not l.startswith("##")]
df = pd.read_csv(io.StringIO("".join(vcf_lines)), sep="\t")

df = pd.read_csv("genes.gff3", sep="\t", comment="#",        # GFF/GTF
     names=["seqid","source","type","start","end","score","strand","phase","attrs"])
df = pd.read_csv("regions.bed", sep="\t", header=None,       # BED
     names=["chrom","start","end","name","score","strand"])

import pysam                                                  # BAM (requires pysam)
bam = pysam.AlignmentFile("aligned.bam", "rb")
for read in bam.fetch("chr1", 1000, 2000): print(read.query_name)
```

### Structural
```python
from Bio.PDB import PDBParser, MMCIFParser
parser = PDBParser(QUIET=True)
structure = parser.get_structure("prot", "structure.pdb")     # PDB

parser = MMCIFParser(QUIET=True)
structure = parser.get_structure("prot", "structure.cif")     # mmCIF

from rdkit import Chem                                        # SDF/MOL (requires rdkit)
supplier = Chem.SDMolSupplier("compounds.sdf")
mols = [m for m in supplier if m is not None]
```

### Omics Matrices
```python
import anndata
adata = anndata.read_h5ad("expression.h5ad")                 # AnnData (scRNA-seq, spatial)

import scipy.io
mat = scipy.io.mmread("matrix.mtx")                          # 10X Genomics MTX
barcodes = pd.read_csv("barcodes.tsv", header=None)[0].tolist()
features = pd.read_csv("features.tsv", sep="\t", header=None)[1].tolist()

df = pd.read_csv("expression.gct", sep="\t", skiprows=2)     # GCT (gene expression)

import loompy                                                 # Loom (legacy single-cell)
ds = loompy.connect("data.loom")
```

### Mass Spectrometry & Flow Cytometry
```python
from pyteomics import mzml                                    # mzML (proteomics, requires pyteomics)
spectra = list(mzml.read("spectra.mzML"))

import fcsparser                                              # FCS (flow cytometry, requires fcsparser)
meta, data = fcsparser.parse("sample.fcs", reformat_meta=True)
```

### Neuroimaging
```python
import nibabel as nib                                         # NIfTI (requires nibabel)
img = nib.load("brain.nii.gz")
data = img.get_fdata()  # 3D/4D numpy array

# DICOM (requires pydicom)
import pydicom
dcm = pydicom.dcmread("scan.dcm")
pixel_data = dcm.pixel_array
```

### Phylogenetics & Systems Biology
```python
from Bio import Phylo                                         # Newick/Nexus (BioPython)
tree = Phylo.read("tree.nwk", "newick")
tree = Phylo.read("tree.nex", "nexus")

import libsbml                                                # SBML (systems biology, requires python-libsbml)
reader = libsbml.SBMLReader()
doc = reader.readSBML("model.xml")
model = doc.getModel()
```

### Serialized
```python
import json, xml.etree.ElementTree as ET, h5py

data = json.load(open("data.json"))                           # JSON
df = pd.read_json("records.json")                             # JSON -> DataFrame
tree = ET.parse("data.xml"); root = tree.getroot()            # XML
f = h5py.File("data.h5", "r"); dataset = f["group/data"][:]   # HDF5
```

### Compressed
```python
df = pd.read_csv("data.csv.gz")                              # gzip (pandas auto-detects)
df = pd.read_csv("data.tsv.gz", sep="\t")                    # gzip TSV

import zipfile
with zipfile.ZipFile(io.BytesIO(content)) as z:               # ZIP
    df = pd.read_csv(z.open(z.namelist()[0]))

import tarfile
with tarfile.open("archive.tar.gz") as t:                     # tar.gz
    f = t.extractfile(t.getnames()[0])
    df = pd.read_csv(f)
```

---

## Section B: API Patterns by Domain

Each category shows: which ToolUniverse tools exist, and how to go beyond them with direct API calls.

### 1. NCBI E-utilities (Gene, Nucleotide, Protein, SRA, GEO)
Tools: `NCBI_search_gene`, `NCBI_search_nucleotide`, `SRA_search_runs`, `GEO_search_datasets`
```python
import requests
base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
# Search -> get IDs -> fetch records in batches
ids = requests.get(f"{base}/esearch.fcgi?db=gene&term=BRCA1+AND+human&retmax=500&retmode=json").json()
id_list = ids["esearchresult"]["idlist"]
# Fetch in batches of 500
for i in range(0, len(id_list), 500):
    batch = ",".join(id_list[i:i+500])
    data = requests.get(f"{base}/efetch.fcgi?db=gene&id={batch}&retmode=xml").text
```

### 2. EBI APIs (UniProt, PDBe, ChEMBL, Ensembl, InterPro)
Tools: `UniProt_search`, `PDBe_*`, `ChEMBL_*`, `Ensembl_*`, `InterPro_*`
```python
# UniProt bulk TSV download with cursor pagination
url = "https://rest.uniprot.org/uniprotkb/search?query=organism_id:9606+AND+keyword:kinase&format=tsv&size=500"
all_rows = []
while url:
    resp = requests.get(url)
    all_rows.append(resp.text)
    url = resp.headers.get("Link", "").split(";")[0].strip("<>") if "Link" in resp.headers else None
```

### 3. NCI GDC (TCGA/TARGET Cancer Data)
Tools: `GDC_search_cases`, `GDC_list_files`, `GDC_get_clinical_data`
```python
# Bulk clinical data with filters
filters = {"op":"and","content":[
    {"op":"=","content":{"field":"project.project_id","value":"TCGA-BRCA"}},
    {"op":"=","content":{"field":"demographic.vital_status","value":"Dead"}}
]}
cases = requests.post("https://api.gdc.cancer.gov/cases", json={
    "filters": filters, "fields": "demographic.vital_status,diagnoses.days_to_death",
    "size": 1000, "from": 0
}).json()["data"]["hits"]
```

### 4. CDC Health Surveys (NHANES, BRFSS, WONDER)
Tools: `NHANES_download_and_parse`, `cdc_data_search_datasets`
```python
# Direct NHANES XPT download (any cycle, any component)
cycle, component = "2017-2018", "DEMO_J"
url = f"https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/{component}.XPT"
df = pd.read_sas(io.BytesIO(requests.get(url).content), format="xport")
```

### 5. GWAS & Genetics (GWAS Catalog, gnomAD, ClinVar)
Tools: `gwas_search_associations`, `gnomAD_*`, `ClinVar_*`
```python
# GWAS Catalog full download (37MB TSV, all associations)
url = "https://www.ebi.ac.uk/gwas/api/search/downloads/alternative"
df = pd.read_csv(url, sep="\t")
# Filter locally
hits = df[df["DISEASE/TRAIT"].str.contains("diabetes", case=False, na=False)]
```

### 6. Chemical (PubChem, ChEMBL, KEGG)
Tools: `PubChem_*`, `ChEMBL_*`, `KEGG_*`
```python
# PubChem batch property retrieval (up to 100 CIDs at once)
cids = "2244,5988,3672"  # aspirin, sucrose, ibuprofen
url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cids}/property/MolecularWeight,XLogP,TPSA/JSON"
props = requests.get(url).json()["PropertyTable"]["Properties"]
```

### 7. Expression (GEO, ArrayExpress, GTEx)
Tools: `GEO_search_datasets`, `ArrayExpress_search`
```python
# GEO series matrix direct download
geo_id = "GSE12345"
url = f"https://ftp.ncbi.nlm.nih.gov/geo/series/{geo_id[:5]}nnn/{geo_id}/matrix/{geo_id}_series_matrix.txt.gz"
df = pd.read_csv(url, sep="\t", comment="!", index_col=0)

# GTEx bulk expression (median TPM per tissue)
url = "https://storage.googleapis.com/adult-gtex/bulk-gex/v8/rna-seq/GTEx_Analysis_2017-06-05_v8_RNASeQCv1.1.9_gene_median_tpm.gct.gz"
df = pd.read_csv(url, sep="\t", skiprows=2)
```

### 8. Clinical (ClinicalTrials.gov, FDA/OpenFDA, FAERS)
Tools: `search_clinical_trials`, `OpenFDA_*`
```python
# ClinicalTrials.gov v2 API with pagination
all_studies = []
token = None
while True:
    params = {"query.cond": "lung cancer", "query.intr": "immunotherapy", "pageSize": 100}
    if token: params["pageToken"] = token
    resp = requests.get("https://clinicaltrials.gov/api/v2/studies", params=params).json()
    all_studies.extend(resp.get("studies", []))
    token = resp.get("nextPageToken")
    if not token: break
```

### 9. Literature (PubMed, PMC, EuropePMC)
Tools: `PubMed_search_articles`, `EuropePMC_search_articles`
```python
# EuropePMC full-text search with cursor
cursor = "*"
all_results = []
while cursor:
    resp = requests.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
        params={"query": "BRCA1 AND resistance", "format": "json", "pageSize": 100, "cursorMark": cursor}).json()
    all_results.extend(resp.get("resultList", {}).get("result", []))
    cursor = resp.get("nextCursorMark") if len(all_results) < resp.get("hitCount", 0) else None
```

### 10. Data Repositories (Zenodo, Figshare, Dryad, DataCite)
Tools: `DataCite_search_dois`, `Zenodo_search_records`, `Dryad_search_datasets`
```python
# Zenodo: search + download files
record = requests.get("https://zenodo.org/api/records", params={"q": "proteomics cancer", "size": 5}).json()["hits"]["hits"][0]
for f in record["files"]:
    content = requests.get(f["links"]["self"]).content  # download each file
```

### 11-24. Specialized Domains

For these 14 additional domains, read [references/specialized-domains.md](references/specialized-domains.md) when you need the specific API pattern:

| # | Domain | Key APIs/Tools | When to Read |
|---|--------|---------------|--------------|
| 11 | Proteomics | PRIDE, MassIVE, ProteomeXchange | Mass spec data download |
| 12 | Metabolomics | MetaboLights, Metabolomics Workbench, HMDB | Metabolite/spectra data |
| 13 | Microbiome | MGnify, GMREPO | Metagenome profiles |
| 14 | Ecology | GBIF, iNaturalist, OBIS | Species occurrence data |
| 15 | Model Organisms | FlyBase, WormBase, ZFIN, RGD | Gene data for non-human species |
| 16 | Pathways & Networks | Reactome, STRING, BioGRID | Network/pathway export |
| 17 | Ontologies | OLS, GO, HPO | Term hierarchy traversal |
| 18 | Immunology | IEDB, VDJdb, ImmPort | Epitope/receptor data |
| 19 | Drug & Pharma | PharmGKB, DGIdb, SIDER | Drug-gene interactions |
| 20 | Imaging & Atlases | TCIA, HPA, Allen Brain Atlas | Imaging collections |
| 21 | Protein Structure | RCSB PDB, AlphaFold | PDB/CIF file download |
| 22 | Clinical Genomics | ClinVar, ClinGen, CIViC | Variant interpretation bulk |
| 23 | Single-Cell | cellxgene, ARCHS4 | scRNA-seq data portals |
| 24 | Toxicology | CTD, EPA CompTox | Chemical-gene-disease |

---

## Section C: Restricted/Uncovered Data Sources

These sources require registration or have no ToolUniverse tool. For each, the table shows access requirements and how to get data programmatically once credentialed.

**Note**: ToolUniverse has 2300+ tools — use `find_tools("your topic")` to discover tools not listed above. Section B covers the most common API *patterns*; many more databases use the same patterns (e.g., all EBI databases follow the EBI REST pattern in #2).

| Source | Access | Wait Time | Format | Contents |
|--------|--------|-----------|--------|----------|
| **UK Biobank** | Restricted (institutional) | 2-6 months | CSV/Bulk | 500K participants, genetics + imaging + health records |
| **dbGaP** | Controlled (PI application) | 1-3 months | SRA/VCF/phenotype | GWAS genotypes + phenotypes from thousands of studies |
| **MIMIC-IV** | Credentialed (PhysioNet) | 1-2 weeks | CSV/Parquet | ICU clinical data, 300K+ admissions |
| **ICPSR** | Registration | 1-3 days | Stata/CSV | Social/health science archives (10K+ studies) |
| **HRS** | Registration | 1-3 days | Stata | Health & Retirement Study, 20K+ older Americans, biennial |
| **ELSA** | Registration | 1-3 days | Stata/SPSS | English Longitudinal Study of Ageing |
| **SHARE** | Registration | 1-2 weeks | Stata | Survey of Health, Ageing, Retirement in Europe (28 countries) |
| **Materials Project** | Free API key | Instant | JSON | 150K+ computed materials properties |
| **Human Cell Atlas** | Open | Instant | h5ad/loom | Single-cell atlas across human tissues |
| **ADNI** | Application | 1-2 months | DICOM/CSV | Alzheimer's neuroimaging + biomarkers + cognition |
| **OpenNeuro** | Open | Instant | NIfTI/BIDS | 800+ neuroimaging datasets |
| **CIBERSORTx** | Free registration | Instant | GCT/TSV | Cell type deconvolution from bulk expression |
| **FlowRepository** | Open | Instant | FCS | Flow cytometry experiments |
| **SynBioHub** | Open | Instant | SBOL/GenBank | Synthetic biology parts and designs |

For restricted sources: search literature (PubMed) for published analyses using that dataset. Papers cite their data source and often deposit derived data in public repositories (GEO, SRA, Zenodo).

---

## Section D: Universal Patterns

### Pagination
```python
# Pattern 1: offset + limit (most REST APIs)
all_records = []
offset = 0
while True:
    resp = requests.get(f"{api_url}?offset={offset}&limit=500", timeout=30).json()
    batch = resp.get("data", resp.get("results", resp.get("hits", [])))
    if not batch: break
    all_records.extend(batch)
    offset += len(batch)

# Pattern 2: cursor/token (EuropePMC, ClinicalTrials.gov, UniProt)
token = None
while True:
    params = {"pageSize": 100}
    if token: params["pageToken"] = token
    resp = requests.get(api_url, params=params).json()
    all_records.extend(resp["results"])
    token = resp.get("nextPageToken")
    if not token: break
```

### Rate Limiting & Retries
```python
import time
def fetch_with_retry(url, max_retries=3, **kwargs):
    for attempt in range(max_retries):
        resp = requests.get(url, timeout=30, **kwargs)
        if resp.status_code == 200: return resp
        if resp.status_code == 429:  # rate limited
            wait = int(resp.headers.get("Retry-After", 2 ** attempt))
            time.sleep(wait)
        else:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed after {max_retries} retries: {url}")
```

### Authentication
```python
import os
# API key in header (most common)
headers = {"Authorization": f"Bearer {os.environ.get('API_KEY', '')}"}
# API key as query param
params = {"api_key": os.environ.get("API_KEY", "")}
# No auth needed for most scientific APIs (NCBI, EBI, PubChem, GDC, CDC)
```

### Bulk Download with Streaming
```python
def download_large_file(url, output_path):
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
```

### Error Handling
```python
resp = requests.get(url, timeout=30)
if resp.status_code != 200:
    raise ValueError(f"HTTP {resp.status_code}: {resp.text[:200]}")
# Guard against HTML error pages (CDC, NCBI return 200 with HTML for missing files)
if resp.content[:5] in (b"<!DOC", b"<html"):
    raise ValueError(f"Server returned HTML error page for {url}")
data = resp.json()  # raises JSONDecodeError if not valid JSON
```
