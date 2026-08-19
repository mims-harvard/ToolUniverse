#!/usr/bin/env python3
"""Case 3: Is BCG vaccination associated with higher adverse-event severity?

Reproduces the third case study from
https://aiscientist.tools/posts/tooluniverse-case-studies

Unlike Cases 1 and 2, this is statistics on raw tabular data rather than
database lookups: one tool, ``clinical_trial_ae_severity_test``, used in three
modes (prepare, chi-square, ordinal) on the public BCG-CORONA trial tables.

This case reproduces exactly, to the published decimal places, because the
input is a frozen public dataset rather than a live database. The severity
distribution checked in step 1 is reported in the supplementary note
(arXiv:2509.23426); the other values are in the post itself.

Setup:
    python download_bcg_data.py     # ~4 MB from Zenodo, CC0
    python case3_bcg_ae_severity.py

The analysis runs through the ``clinical_trial_ae_severity_test`` tool, the
same tool the AI scientist used. That tool loads its implementation from the
repository's ``skills/`` directory, so it only resolves in a git clone. When it
is unavailable -- a plain ``pip install``, for instance -- this script falls
back to the equivalent implementation bundled alongside it in ``scripts/``,
reports which path it took, and produces the same numbers either way.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _common import call, footer, header, is_error, load_universe, report, step

# Bundled equivalent of the skill script the tool wraps, used when the tool
# cannot locate its own implementation (see the module docstring).
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

DM_FILE = "TASK008_BCG-CORONA_DM.csv"
AE_FILE = "TASK008_BCG-CORONA_AE.csv"

# Patient-interaction covariates, as recorded in the trial's demographics table.
COVARIATES = "patients_seen,expect_interact,work_hours"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data",
        type=Path,
        default=Path(__file__).parent / "data",
        help="Directory holding the BCG-CORONA CSVs (default: ./data)",
    )
    args = parser.parse_args()

    dm, ae = args.data / DM_FILE, args.data / AE_FILE
    if not dm.exists() or not ae.exists():
        raise SystemExit(
            f"Trial tables not found in {args.data}.\nRun:  python download_bcg_data.py"
        )

    header(
        "Case 3: BCG vaccination and adverse event severity",
        "In the public BCG-CORONA healthcare-worker trial, is BCG vaccination\n"
        "          associated with higher adverse-event severity after adjusting for\n"
        "          patient-interaction frequency?",
    )
    tu = load_universe(["clinical_trial_stats"])
    common = {"dm_file": str(dm), "ae_file": str(ae), "group_col": "TRTGRP"}

    def analyse(test, **extra):
        """Run one mode through the tool, or the bundled script if it is absent.

        The tool resolves its implementation relative to the repository root, so
        outside a git clone it reports "Skill script not available". Rather than
        fail, fall back to the copy bundled under scripts/ and say so.
        """
        result = call(
            tu, "clinical_trial_ae_severity_test", test=test, **extra, **common
        )
        if not is_error(result):
            return result, "tool"
        if "Skill script not available" not in str(result["__error__"]):
            raise SystemExit(f"{test} failed: {result['__error__']}")

        import prepare_ae_cohort as script

        df = script.prepare_cohort(str(dm), str(ae), "")
        out = {
            "n_subjects": len(df),
            "aesev_distribution": {
                int(k): int(v)
                for k, v in df["AESEV"].value_counts().sort_index().to_dict().items()
            },
        }
        if test == "chi-square":
            chi2, pval, dof, table = script.run_chi_square(df, "TRTGRP")
            out |= {
                "test_statistic": chi2,
                "p_value": pval,
                "dof": dof,
                "contingency_table": table,
            }
        elif test == "ordinal":
            covs = [c for c in extra.get("covariates", "").split(",") if c]
            fit = script.run_ordinal(df, "TRTGRP", covs)
            primary = fit["odds_ratios"]["TRTGRP"]
            out |= {
                "or": primary["or"],
                "ci_lower": primary["ci_lower"],
                "ci_upper": primary["ci_upper"],
                "p_value": primary["p_value"],
                "odds_ratios": fit["odds_ratios"],
            }
        return out, "bundled script"

    # ------------------------------------------------------------------
    step(1, "Construct the analysis cohort  (prepare mode)")
    prepared, via = analyse("prepare")
    print(f"  (running via: {via})")
    report("evaluable subjects", prepared["n_subjects"], "791")
    report(
        "max-severity distribution",
        prepared["aesev_distribution"],
        "{1: 328, 2: 402, 3: 43, 4: 18}",
    )
    print("  Each subject is reduced to their maximum AESEV grade across all")
    print("  adverse events, inner-joined onto demographics on USUBJID.")

    # ------------------------------------------------------------------
    step(2, "Test for an unadjusted association  (chi-square mode)")
    chi, _ = analyse("chi-square")
    report("chi-square", f"{chi['test_statistic']:.2f}", "10.12")
    report("degrees of freedom", chi["dof"], "3")
    report("p-value", f"{chi['p_value']:.3f}", "0.018")
    print("  Treatment-by-severity contingency table:")
    for group, row in (chi.get("contingency_table") or {}).items():
        counts = "  ".join(f"{grade}:{n:>4}" for grade, n in sorted(row.items()))
        print(f"    {group:<10} {counts}")

    # ------------------------------------------------------------------
    step(3, "Fit an adjusted model  (ordinal mode)")
    ordinal, _ = analyse("ordinal", covariates=COVARIATES)

    # The tool reports the odds ratio against its own reference level. Treatment
    # is encoded alphabetically (BCG=0, Placebo=1), so the raw OR is Placebo vs
    # BCG and the published direction is its reciprocal.
    raw_or = ordinal["or"]
    or_bcg = 1 / raw_or
    ci_low, ci_high = 1 / ordinal["ci_upper"], 1 / ordinal["ci_lower"]

    report("raw OR (Placebo vs BCG)", f"{raw_or:.4f}", "0.65")
    report("OR for higher severity with BCG", f"{or_bcg:.2f}", "1.53")
    report("95% CI", f"({ci_low:.2f}, {ci_high:.2f})", "(1.16, 2.01)")
    report("p-value", f"{ordinal['p_value']:.4f}", "0.0024")
    print("  Covariates (none significant, as published):")
    for name, stats in (ordinal.get("odds_ratios") or {}).items():
        if name != "TRTGRP":
            print(f"    {name:<20} OR={stats['or']:.3f}  p={stats['p_value']:.3f}")

    footer(
        {
            "Unadjusted and adjusted": "agree on a significant association between BCG "
            "and higher maximum AE severity",
            "Not independent": "the two tests share the outcome and overlapping data",
            "Interpretation": "an association, not a causal effect: the cohort is "
            "restricted to subjects with at least one AE and the endpoint is a "
            "derived per-subject maximum",
            "Caveat": "the proportional-odds assumption should be checked before the "
            "single OR is over-interpreted",
        }
    )


if __name__ == "__main__":
    main()
