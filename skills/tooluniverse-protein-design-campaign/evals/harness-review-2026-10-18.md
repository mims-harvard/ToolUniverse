# Targeted campaign-learning harness review

Scope: the current TU discovery and test-harness workflow, using public/synthetic
controls and two read-only researcher personas. This is not an external benchmark,
biological calibration, or a claim that every ToolUniverse tool passed.

Functional discovery found the existing PROPKA predictors and same-coordinate
primary-partner comparison. Their documented scope did not include integration
of a caller's complete bound/free component inventory, so a separate local
postprocessor was added rather than another pKa predictor.

The pH researcher exercised identity cancellation, analytic sign/base-ten
conversion, manual identity correspondence, incomplete coverage, explicit
molecular copies, reference conventions and numerical boundaries through the
registered SDK and CLI. The campaign reviewer exercised exact reuse, preparation
controls, a failed paired parent, assay endpoints, free references and receipt
verification. Neither persona edited the implementation. Reports were checked
against reachable interfaces before changes.

One implementation issue surfaced in both personas: explicit null temperature
passed the declared schema but failed the SDK and CLI route. It now defaults to
298.15 K, with a real-SDK regression and a CLI retest. The standalone skill now
includes its runnable analytic example; generated plugin copies were synchronized.

Scientific acceptance checks include:

- One HIS shifts from free pKa 6 to bound pKa 7: at pH 7 versus reference 6,
  log10 association = −0.48072537898848766 and conditional linkage energy =
  +0.6558281623747966 kcal/mol at 298.15 K.
- Finite-difference slope agrees with negative bound-minus-free proton uptake.
- Component and terminal/nonterminal subtotals sum to the aggregate.
- Explicitly expanded molecular copies scale the total; a missing copy rejects.
- Missing, extra, duplicate, unresolved and nonfinite groups never silently
  become a complete intersection.
- Extreme finite pKas remain stable, reference reversal changes sign and
  temperature scales energy without changing the logarithmic trend.
- Structural completeness and experimental verification always remain false.

The updated skill also retains negative results, requires parent/mutant starting-pose
re-preparation controls, separates acid-wash retention from equilibrium affinity,
keeps partial-site/learned-unit scope visible, and treats a queued request that
never starts as zero model calls. Its eight behavioral prompts are evaluations,
not eight laboratory experiments or an automated accuracy score.

Existing PROPKA numeric tests need the optional `protein-pka` dependency. The
new postprocessor itself has no optional model dependency. Local SDK checks used
the supported light-import mode because the pre-existing environment's FastMCP
settings were incompatible with ordinary import; no unrelated compatibility
change was bundled into this feature.

Final targeted regression: 151 tests passed after installing PROPKA 3.5.1 in
a temporary dependency directory (no shared environment modification). The
registered public 1UBQ PROPKA-to-linkage identity control matched all 26 groups
against an independently enumerated coordinate/terminal inventory and returned
zero relative terms. Tool config execution and return-schema validation passed;
documentation validation checked 1,359 Python blocks with zero issues. These
are software and analytic controls, not biological validation.
