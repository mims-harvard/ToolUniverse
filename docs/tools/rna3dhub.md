# RNA 3D Hub: representative sets and the RNA 3D Motif Atlas

The [BGSU RNA 3D Hub](https://rna.bgsu.edu/rna3dhub) (Bowling Green State University) annotates every RNA-containing PDB structure each week. It groups the RNA chains into equivalence classes with one representative each (the non-redundant set used for RNA 3D work), and it clusters the hairpin, internal and junction loops of the representative structures into 3D motif groups (the RNA 3D Motif Atlas). The four tools read the public download routes. No key is needed. The data licence is CC BY 4.0.

| Tool | Use it to |
|---|---|
| `RNA3DHub_get_representative_set` | Read the equivalence classes at a resolution cutoff, or find the class and representative of one PDB entry (`pdb_id`). |
| `RNA3DHub_list_motifs` | List the motif groups of one loop type (`HL`, `IL`, `J3` to `J7`), e.g. `query="GNRA"`. |
| `RNA3DHub_get_motif` | Read the loops of one motif group, aligned position by position. |
| `RNA3DHub_get_structure_loops` | List the loops annotated in one PDB entry, with their sequences. |

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools(categories=["rna3dhub"])
loops = tu.tools.RNA3DHub_get_structure_loops(pdb_id="4TNA")
# yeast tRNA-Phe: 4 hairpin loops and the 4-way junction J4_4TNA_001
# loops["data"][0]["sequence"] == "CAG(H2U)(H2U)GGGAG"   (the D-loop)
```

A chain id reads `PDB|model|chain` (`4TNA|1|A`) and a unit id adds the residue and its number (`4TNA|1|A|G|15`). Chains that form one unit are joined with `+`. A modified residue is written in brackets in `sequence`.

Three habits of the server are handled:

- The row order of the representative set changes between requests. The tool sorts by `class_id`, so `offset` paging is stable.
- An unknown release answers HTTP 200 with the text `Invalid release id`. The tool returns an error.
- `No loops found` (HTTP 200) is the answer for an RNA with no loop and for an id that the Hub does not hold, such as a protein entry or a typo. The tool looks the id up in the current representative set: a known RNA gives an empty list with a note, and any other id gives an error.

A multi-model entry (NMR) has one row per loop per model in the Hub: 2KZL has 8 models, so its 1 hairpin loop and 4 internal loops come back as 40 rows. Each row has its `model`, `metadata.model_count` gives the number of models, and the note says that the counts cover all models. `model=1` keeps one model.

Most motif groups have no group name in the Atlas. The names (GNRA, T-loop, kink-turn) are annotations of the single loops, so `RNA3DHub_list_motifs` returns them as `instance_annotations` with a count, and `query` searches them.

Cite Petrov, Zirbel and Leontis, RNA 2013 (doi:10.1261/rna.039438.113) for the Motif Atlas and Leontis and Zirbel 2012 (doi:10.1007/978-3-642-25740-7_13) for the representative sets.
