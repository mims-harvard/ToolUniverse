# PubMLST sequence typing

[PubMLST](https://pubmlst.org) (University of Oxford) holds the reference alleles and sequence types (STs) for multilocus sequence typing (MLST), core-genome MLST and other schemes of about 90 bacterial and eukaryotic groups. The four tools use the public REST API at `https://rest.pubmlst.org`. No key is needed.

| Tool | Use it to |
|---|---|
| `PubMLST_list_databases` | Find the database of an organism group, e.g. `neisseria` -> `pubmlst_neisseria_seqdef`. |
| `PubMLST_list_schemes` | List the schemes of a database. Scheme 1 is usually the 7-locus MLST scheme. |
| `PubMLST_get_profile` | Read the allele at each locus, and fields such as the clonal complex, for one ST. |
| `PubMLST_type_sequence` | Type one locus or a FASTA of assembly contigs: exact alleles and, when all loci match, the ST. |

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools(categories=["pubmlst"])
profile = tu.tools.PubMLST_get_profile(
    database="pubmlst_neisseria_seqdef", scheme_id=1, st=11
)
# ST 11, ST-11 complex: abcZ 2, adk 3, aroE 4, fumC 3, gdh 8, pdhC 4, pgm 6
```

`database` takes the full database name or the group name from `PubMLST_list_databases`.

Without a login, PubMLST serves only data submitted on or before a cutoff date (2024-12-31 on 2026-11-18). A newer record, such as Neisseria ST 20000, answers HTTP 403, and the tool error quotes PubMLST's notice. An ST that does not exist answers 404 "does not exist". Some groups, such as rMLST, need a login for all data; `long_description` in `PubMLST_list_databases` says so.

`database` must be a sequence-definition (`_seqdef`) database. An isolates database is rejected, because its scheme ids are not the same.

`PubMLST_type_sequence` returns an empty `exact_matches` for a novel allele, not an error. Set `partial_matches=true` to get the closest allele, its identity and its mismatch count for each locus without an exact match. The tool leaves out the allele and flanking sequences, which are long for a whole assembly.
