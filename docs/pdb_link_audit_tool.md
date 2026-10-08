# Explicit PDB LINK distance comparison

`PDB_compare_declared_links` compares reference coordinate distances for explicit legacy-PDB `LINK` declarations against another local PDB. Both inputs can be local paths or inline text and are limited to 4 MiB each. No scientific coordinates are sent to any service. Exactly one source is required for each input. Unused source parameters may be null.

The tool selects one model by file order from each file. Every LINK endpoint must resolve to exactly one atom with the declared residue name, chain, residue number, insertion code, atom name, and explicit alternate location if supplied. Blank LINK alternate locations do not choose between coordinate alternatives. Missing or ambiguous endpoints are reported as unresolved and prevent overall agreement.

Renamed chains require `chain_map`. Renumbered residues require explicit `residue_map` entries; the tool never aligns sequences, builds residues, or infers offsets. Mappings that collapse distinct reference atoms are rejected. Crystal symmetry links requiring transformed coordinates, duplicate declarations, and references without LINK records are rejected rather than producing a vacuous pass.

The default maximum absolute distance deviation is 0.3 Angstrom. Distances are measured from reference coordinates, not the optional LINK distance field, and reference geometry is not assumed chemically valid. An observed file need not retain its own LINK records: the explicit reference provides the audited identities. File hashes identify both actual inputs and caching is disabled.

A successful tool call can still report `all_declared_distances_agree: false`. Even agreement is only a coordinate diagnostic. SSBOND/CONECT records, bond inference, atom aliases, ideal bond lengths, stereochemistry, valence, nonbonded clashes, glycan conformational ensembles, affinity, and pH selectivity are outside its scope.

The bundled example uses two synthetic atoms and a deliberately stretched connection; it contains no experimental or private candidate data.
