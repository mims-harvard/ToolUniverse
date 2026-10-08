# Local protein MSA input diagnostics

`Protein_MSA_inspect` reads one local alignment or inline text, returning counts and hashes without sequence/header output or network requests. Call separately for each complex component: a receptor MSA does not establish ligand MSA depth.

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools(tool_type=["protein_msa"])
result = tu.run_one_function({
    "name": "Protein_MSA_inspect",
    "arguments": {"alignment_content": ">query\nACDE\n", "expected_query_sequence": "ACDE"},
})
```

The first record is the query. Raw row count, unique aligned rows, duplicate rows, all-gap rows, distinct nonempty nonquery rows, expected-query match, query-column identity/coverage and insertion counts are separate fields. Duplicate-only alignments are reported distinctly from single-row query-only inputs. A mismatch is a diagnostic result, not a transport error.

A3M removes lowercase insertion residues and insertion dots before equal-length checks. Aligned FASTA normalizes lowercase and maps dots to gaps. Identity includes gaps as nonmatches at the query's nongap columns; coverage uses the same denominator. No sequence weighting or Neff is computed. Counts do not verify evolutionary homology, paired provenance, model readiness, folding accuracy or binding. ColabFold length/complex metadata is rejected; supply component alignments instead.

Bounds: 8 MiB input, 20,000 rows, 10,000 columns and at most 100 row summaries (default 10). Files are read without modification. Aggregate counts stay complete when row details are truncated. Malformed records and nonprotein characters return a schema-valid error.

Validation fixtures are explicitly synthetic alignments for parsing diagnostics, not invented database identifiers or claims of real homologs.
