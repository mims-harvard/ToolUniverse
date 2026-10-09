# Local protein similarity

These tools run caller-managed CPU executables and references on the
ToolUniverse host. They do not query the MMseqs2 or Foldseek web services,
download databases, install software, or alter the input files. Paths are on
the tool host, which can differ from the agent's machine when using remote MCP.

Install the CPU binaries using the official [MMseqs2](https://github.com/soedinglab/MMseqs2)
and [Foldseek](https://github.com/steineggerlab/foldseek) instructions. Put
`mmseqs`/`foldseek` on the host's PATH, or configure
`TOOLUNIVERSE_MMSEQS2_BINARY` and `TOOLUNIVERSE_FOLDSEEK_BINARY` with their
executable paths. Neither is a Python import or a base-package dependency.
Missing binaries return an actionable dependency error, without an online
fallback. No API key is used.

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools(tool_type=["protein_similarity_local"])
sequence = tu.tools.ProteinSimilarity_search_sequence_local(
    query_path="candidate_sequences.fasta",
    reference_path="reviewed_proteins.fasta",
    minimum_query_coverage=0.7,
)
structure = tu.tools.ProteinSimilarity_search_structure_local(
    query_path="single_chain_models",
    reference_path="local_foldseek_pdb_database",
)
```

Sequence queries are uppercase standard amino acids/X, without gaps or stops,
with unique FASTA identifiers, at most 50 proteins and 10,000 residues/protein.
Structure queries are single-model, single-chain standard-protein PDB files,
or a directory with 1–50 such `.pdb` files; explicitly extract the intended
binder instead of accidentally searching its receptor. Each query file is
limited to 2 MiB. The CA checks are basic input checks, not complete chemical
or stereochemical validation. Query contents are staged from the validated
snapshot. References are a local FASTA/PDB file or a prebuilt database prefix
with its `.dbtype` file; maintain a fixed reference snapshot during a call.

For a public calibration that also works from an installed package, explicitly
set both paths to `builtin:1UBQ`. This selects bundled experimental protein
coordinates or the matching 76-residue sequence from
[ubiquitin 1UBQ](https://www.rcsb.org/structure/1UBQ). It does not send a PDB ID
to a service and is never a default replacement for missing input.

MMseqs2 uses protein search, sensitivity 7.5, exact alignment identities and a
2 GiB split-memory budget. The default reported E-value cutoff is 0.001.
Foldseek uses TM-align, CPU ungapped prefiltering, and explicit exact TM-score
output. It reports both query- and target-normalized scores, which differ for
unequal protein lengths. It requests `qtmscore` and `ttmscore`; the separate
native `alntmscore` field is omitted (the pinned public 1UBQ self-control
returned 1.013 for that field while both normalized exact scores were 1.000).
`fident`, `qcov`, `tcov` and the returned normalized TM-scores are fractions
in 0–1, not percentages. Within each query, sequence hits are ranked by bit
score and structure hits by query-normalized TM-score. Output truncation and
the backend hit count are explicit; no-hit queries still count in the inputs.

CPU threads default to 2 (maximum 8), and runtime to 300 seconds (maximum
3600). Timed-out owned process groups are stopped on POSIX. Temporary outputs
are removed. Path-based calls are not cached. Binary version/hash and query
fingerprints make the calculation traceable; the full reference database is
not fingerprinted by the tool.

Similarity does not establish affinity, pH selectivity, function or novelty.
No hit searches only the supplied reference snapshot. Whole-chain TM-align
does not reproduce consensus domain segmentation or an official novelty
classifier. Consequently `novelty_certified` and `binding_verified` stay false.
