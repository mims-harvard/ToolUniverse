### GTEx Examples (Expression)

About GTEx
- GTEx provides tissue-specific gene expression and eQTL data across a wide range of human tissues, accessible via public APIs and downloads.

Run:
```bash
python examples/expression/gtex/use_gtex.py
```

What it does:
- GTEx_get_expression_summary: summarize expression for a given gene
- GTEx_query_eqtl: query eQTL records for a gene (paged)

Notes:
- API endpoints can be large; reduce page/size for quick tests.
- Tool names assume corresponding tools exist in ToolUniverse.
