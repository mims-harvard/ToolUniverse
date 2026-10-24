# Targeted disagreement and context-control review

Functional discovery through the current SDK catalogue found sequence generation
(`NvidiaNIM_proteinmpnn`), but no matched-backbone conditional-probability ablation
postprocessor. The new local tool fills that analysis gap; it does not add another
generator or assume that the hosted generation interface exposes native conditional
mode. No remote-provider or GPU implementation is bundled.

The source skill now distinguishes ligand fold deformation, receptor-frame placement
and contact register; preserves all coordinate-unique samples; and keeps source-family
and scoring-checkpoint counts separate. It adds matched receptor deletion, prospective
priority versioning and downstream resolution of reused artifacts. The last item is
guidance for campaign readers, not a claim that a ToolUniverse scheduler bug was fixed.

An independent agent used the skill on a local hypothetical scenario and exercised
the packaged analytic control through the actual registered SDK. It distinguished
fold agreement from pose disagreement, retained coordinate aliases as provenance,
cancelled equal full/deleted gains, kept related scorer weights in one family and
resolved an older result before proposing inference. The control returned
0.6931471805599454 nats (ln 2), with coordinate identity and binding verification both
false. The agent reported no interface issue in that SDK route. This is one targeted
forward test, not an accuracy benchmark or a biological calibration.

Deterministic tests cover analytic cancellation and sign, unpaired sample ranges,
alphabet permutation and X normalization, exact declared matrix coverage, mismatched
geometry/sequence/protocol/masks, invalid probability rows, SDK dispatch, public Python
wrapper export, framework validation errors and execution of the reference's Python
block verbatim. The new suite has 35 cases; together with existing campaign preflight
and pH-linkage regressions, 106 tests passed. The config example and its return schema
passed `scripts/test_new_tools.py protein_design_context -v`; the CLI returned the
same analytic value with exit code zero.

These checks validate arithmetic and software contracts. Hashes, masks, source-family
labels and completeness are caller declarations, not independently established
coordinate provenance or coverage of unreported native outputs. Conditional scores
do not establish affinity, activation, pH selectivity or a correct bound pose. The
three added behavioral prompts are evaluation scenarios, not three measured assays.
