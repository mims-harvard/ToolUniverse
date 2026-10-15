# Protein carboxylate groups

PROPKA uses the internal type COO for Asp, Glu and C-terminal carboxyl groups. The ToolUniverse worker reports these protein groups as ASP, GLU and C-, respectively, using the atom's residue and explicit terminal annotation. It preserves the upstream type in propka_group_type. A C-terminal Asp or Glu is labeled C- for its terminal group, so it cannot collide with the side-chain group's comparison key. Ligand COO groups are excluded from protein-group reporting.

Older results silently omitted these groups because the filter expected only ASP, GLU and C-. Successful execution and equal bound/free group counts did not detect that omission. Recompute predictions and any downstream all-group sums made with the older worker; matching coverage alone does not establish chemical completeness. The fix does not change PROPKA's predictions or validate measured affinity or pH selectivity.

The regression fixture is public ubiquitin (1UBQ), with 11 Asp/Glu groups and its terminal carboxyl group. Tests check their known residue positions and unchanged same-coordinate comparison, plus ligand exclusion and terminal-versus-side-chain identity.
