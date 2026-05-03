### GDC Examples (Oncogenomics)

About GDC
- The NCI Genomic Data Commons (GDC) provides access to genomic and clinical data from cancer research programs (e.g., TCGA). Public REST APIs support case, file, and project queries.

Run:
```bash
python examples/oncogenomics/gdc/use_gdc.py
```

What it does:
- GDC_search_cases: search cases within a project (e.g., TCGA-BRCA)
- GDC_list_files: list files filtered by data_type

Notes:
- Some queries may require tokens for controlled-access data; examples use public endpoints.
- Tool names assume corresponding tools exist in ToolUniverse.
