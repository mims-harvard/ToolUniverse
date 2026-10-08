
## Associated components in the free partner

For glycosylated receptors, cofactors, or partners with several constituent chains, explicitly supply free_keep_chains to PROPKA_compare_partner_pka. For example, partner_chain="B", free_keep_chains=["G","H"] extracts B together with those two associated chains. These IDs must exist in coordinate records and must not repeat the primary partner. Omitted or null retains the existing single-chain default.

The caller defines which components belong to the free molecule; this tool does not infer covalent attachment or biological association. Keeping the removed binding partner would not represent a free-state comparison. Reported ionization groups still belong to the chosen primary protein chain, while explicitly retained components remain in its prediction environment. Both inputs use the same coordinates, and the tool does not relax the free state.

Outputs list free_partner_chains, the selected coordinate-record count and the existing free-input hash. Glycan or cofactor pKa values are not reported. Correct composition, matching groups and direction scores do not validate binding affinity or pH selectivity. Assay constructs and terminal states may also differ from a bare-chain model.

The bundled retention example is public ubiquitin coordinates plus one synthetic distant water in chain W. It tests explicit composition retention, not glycan chemistry, and contains no private research data.

Matched and unmatched comparison groups are limited to the chosen primary chain on both sides. Groups from retained auxiliary protein chains remain available in free_prediction but do not falsely appear as missing primary-partner groups.

The generated Python SDK accepts free_keep_chains as well as the registered TU/CLI route. Passing None preserves the single-chain default. CI checks the committed pKa SDK parameter contract before restoring generated SDK caches or rebuilding wrappers, so generation cannot conceal a stale delivered signature.
