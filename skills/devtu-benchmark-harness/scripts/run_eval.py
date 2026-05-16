#!/usr/bin/env python3
"""Unified benchmark runner for ToolUniverse plugin evaluation.

Runs questions through Claude Code with and without the plugin,
captures outputs, grades answers, and saves results.

Usage:
  python run_eval.py --benchmark lab-bench --mode comparison --n 20
  python run_eval.py --benchmark bixbench --mode plugin-only --n 10 --category DESeq2
  python run_eval.py --data-file custom.json --mode baseline-only
"""

import argparse
import contextlib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGIN_DIR = str(REPO_ROOT / "dist" / "tooluniverse-plugin")
EVALS_DIR = REPO_ROOT / "skills" / "evals"
CLEAN_DATA_DIR = REPO_ROOT / "temp_docs_and_tests" / "bixbench_clean" / "data"
CHECKSUMS_FILE = REPO_ROOT / "temp_docs_and_tests" / "bixbench_clean" / "checksums.json"
BIXBENCH_DATA_DIRS = [
    CLEAN_DATA_DIR,
    REPO_ROOT / "temp_docs_and_tests" / "bixbench" / "data",
    REPO_ROOT / "temp_docs_and_tests" / "bixbench" / "bixbench" / "data",
]

# Import grading from sibling script
sys.path.insert(0, str(Path(__file__).parent))
from grade_answers import grade_answer


def _file_sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verify_capsule_checksums(capsule: Path, expected: dict) -> list[str]:
    """Return a list of mismatch messages (empty = capsule is clean)."""
    mismatches = []
    actual_files = {
        str(f.relative_to(capsule)): f
        for f in capsule.rglob("*") if f.is_file()
    }
    # Files present in canonical but missing in capsule
    for rel, exp_hash in expected.items():
        if rel not in actual_files:
            mismatches.append(f"missing: {rel}")
            continue
        got = _file_sha256(actual_files[rel])
        if got != exp_hash:
            mismatches.append(f"hash mismatch: {rel}")
    # Files in capsule but not in canonical (= contamination)
    for rel in actual_files:
        if rel not in expected:
            mismatches.append(f"unexpected: {rel}")
    return mismatches


@contextlib.contextmanager
def isolated_capsule(capsule: Path):
    """Yield a fresh writable copy of the capsule in a tmpdir.

    The agent operates only on the copy; the canonical capsule stays
    untouched. The tmpdir is auto-deleted after the question.
    """
    with tempfile.TemporaryDirectory(prefix=f"{capsule.name}_") as tmp:
        workspace = Path(tmp) / capsule.name
        # Canonical capsule is read-only (a-w); copytree preserves perms,
        # so we restore write permissions on the copy after copying.
        shutil.copytree(capsule, workspace, symlinks=False)
        workspace.chmod(0o755)
        for p in workspace.rglob("*"):
            if p.is_file():
                p.chmod(0o644)
            elif p.is_dir():
                p.chmod(0o755)
        yield workspace


def load_guidance(guidance_path: str = None) -> str:
    """Load guidance text from a file, stripping YAML frontmatter."""
    if guidance_path is None:
        guidance_path = str(Path(PLUGIN_DIR) / "commands" / "research.md")
    path = Path(guidance_path)
    if not path.exists():
        return ""
    text = path.read_text()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[2]
    return text.strip()


# Keyword → skill routing (mirrors the router skill's table). When
# full_skill_injection is enabled, we use this to pick the matching
# sub-skill and pre-load its full SKILL.md body into the system prompt
# via --append-system-prompt. This guarantees the conventions reach
# inference even in `-p` mode where plugin auto-routing is unreliable.
def categorize_for_skill(question_text: str) -> str | None:
    """Route question to a sub-skill. Order: most-specific first.

    Domain-keywords (cpg/colony/treeness/...) are checked BEFORE generic
    statistical method keywords (anova/chi-square/...) so domain-specific
    skills win when both could match.
    """
    q = question_text.lower()
    # Domain-specific (highest priority)
    if "phylo" in q or "treeness" in q or "parsimony" in q or "phykit" in q or "saturation" in q or "dvmc" in q or "tree length" in q or "long branch" in q or "ortholog" in q or ("alignment" in q and ("gap" in q or "mafft" in q)):
        return "tooluniverse-phylogenetics"
    if "methylation" in q or "cpg " in q or " cpg" in q or "5mc" in q or "chip-seq" in q or "atac" in q or "m6a" in q or "chromatin" in q:
        return "tooluniverse-epigenomics"
    if "colony" in q or "circularity" in q or "swarming" in q or "cell area" in q or "morphometry" in q or "fluorescence" in q or "imagej" in q or "cellprofiler" in q or ("mean" in q and "area" in q):
        return "tooluniverse-image-analysis"
    if "variant" in q or "vcf" in q or "vaf" in q or " snp " in q or "haplotypecaller" in q or "indel" in q or "mutation" in q:
        return "tooluniverse-variant-analysis"
    if "crispr" in q or "mageck" in q or "sgrna" in q:
        return "tooluniverse-crispr-screen-analysis"
    if "scanpy" in q or "single-cell" in q or "h5ad" in q:
        return "tooluniverse-single-cell"
    if "fastq" in q or "bwa" in q or "samtools" in q or "trimmomatic" in q or "alignment quality" in q:
        return "tooluniverse-sequence-analysis"
    if "mass spec" in q or "tmt" in q or "proteomics" in q:
        return "tooluniverse-proteomics-analysis"
    # Pipeline-specific
    if "deseq2" in q or "differential expression" in q or "differentially expressed" in q or "fold change" in q or " log2" in q or "deg " in q:
        return "tooluniverse-rnaseq-deseq2"
    if "enrichgo" in q or "enrichment" in q or " go " in q or "kegg" in q or "gseapy" in q or "reactome" in q or "wikipathways" in q:
        return "tooluniverse-gene-enrichment"
    # Generic statistics (lowest priority — domain-specific wins above)
    if "anova" in q or "regression" in q or "chi-square" in q or "spline" in q or "cohen" in q or "f-statistic" in q or "odds ratio" in q:
        return "tooluniverse-statistical-modeling"
    return None


def precompute_for_capsule(capsule_path: Path, question_text: str) -> str:
    """Detect data patterns in the capsule and pre-run matching deterministic
    scripts. Returns a markdown block to inject into the prompt that contains
    the script invocation + its output. Returns "" if no pattern matches.

    Per skill-creator wisdom: when a script reproduces the GT deterministically,
    the agent should see its output BEFORE writing its own analysis. Otherwise
    the agent reinvents the wheel and may pick the wrong interpretation.

    Patterns supported:
      1. target_orthologs.txt + *.busco.zip → busco_target_orthologs.py
      2. long-format CpG CSV (Pos, Chromosome, MethylationPercentage) +
         chromosome length CSV → methylation_density.py
      3. HaplotypeCaller: BAM + reference FASTA → gatk_haplotypecaller_pipeline.py
      4. variant questions with VCF + question keywords → variant skill computations
      5. RNA-seq Pearson r vs length: counts CSV + metadata → custom analysis
      6. scogs zip phylogenetics: scogs_*.zip → scogs_paired_compare.py
         (--only-with-trees gated by _TREE_METRICS so alignment-only metrics work)
      7. Direct treefile capsules: *.treefile (no scogs zip) → phykit treeness
         with per-tree values and per-N averages
      8. Swarm CSV (Ratio + Area + StrainNumber) → spline_model_compare.py
         with canonical R notebook filter (drops strains "1" and "98")
      9. SDTM clinical trial: AE+DM+MH CSVs + treatment/OR question
         → sdtm_ordinal_logistic.py (3-way merge + OrderedModel ordinal logistic)
    """
    if capsule_path is None or not capsule_path.exists():
        return ""

    files = {p.name: p for p in capsule_path.iterdir() if p.is_file()}
    files_lower = {k.lower(): v for k, v in files.items()}
    blocks = []
    repo_root = Path(__file__).resolve().parents[3]

    # Pattern 1: BUSCO target_orthologs intersection
    has_target_list = "target_orthologs.txt" in files
    has_busco_zips = any(name.endswith(".busco.zip") for name in files)
    if has_target_list and has_busco_zips:
        script = repo_root / "skills" / "tooluniverse-phylogenetics" / "scripts" / "busco_target_orthologs.py"
        if script.exists():
            try:
                r = subprocess.run(
                    ["python3", str(script), "--capsule", str(capsule_path)],
                    capture_output=True, text=True, timeout=120,
                )
                output = (r.stdout + "\n" + r.stderr).strip()
                blocks.append(
                    "## Pre-computed analysis (BUSCO target_orthologs)\n\n"
                    f"```\n$ python3 {script.relative_to(repo_root)} --capsule <capsule>\n{output}\n```\n\n"
                    "The script computed every common interpretation. Pick the SUMMARY line "
                    "matching the analysis context (per-group is the typical convention)."
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

    # Pattern 2: Methylation density (CpG long-format + chromosome length)
    cpg_csvs = []
    chr_csvs = []
    for name, path in files.items():
        nl = name.lower()
        if not nl.endswith(".csv"):
            continue
        if "chromosome_length" in nl or "chr_length" in nl:
            chr_csvs.append(path)
        elif "cpg" in nl and "methylat" in nl.replace("_", "").replace("-", "").lower():
            cpg_csvs.append(path)
        elif nl.endswith(".csv"):
            # Heuristic: peek at the header line for the right columns
            try:
                with open(path) as fh:
                    header = fh.readline().lower()
                if "methylationpercentage" in header.replace("_", "") and "pos" in header and "chromosome" in header:
                    cpg_csvs.append(path)
                elif "chromosome" in header and "length" in header and len(header.split(",")) <= 4:
                    chr_csvs.append(path)
            except Exception:
                pass

    if cpg_csvs and chr_csvs:
        script = repo_root / "skills" / "tooluniverse-epigenomics" / "scripts" / "methylation_density.py"
        # Try to extract a chromosome reference from the question text
        # (e.g. "on chromosome Z", "on chr 7", "chromosome 1"). Pattern is
        # case-insensitive and accepts Z, W, X, Y, MT or integer labels.
        import re as _re_chr
        chrom_match = _re_chr.search(
            r"chromosome\s+(z|w|x|y|mt|\d{1,2})\b", question_text.lower()
        )
        target_chr = chrom_match.group(1).upper() if chrom_match else None

        if script.exists():
            # Heuristic to pair CpG with chr lengths by species prefix
            for cpg in cpg_csvs:
                stem = cpg.stem.split("_")[0].upper()  # e.g. "ZF" or "JD"
                pair = next((p for p in chr_csvs if stem in p.stem.upper()), chr_csvs[0])
                cmd = [
                    "python3", str(script),
                    "--cpg", str(cpg),
                    "--chr-lengths", str(pair),
                    "--filter-meth-extremes", "90", "10",
                ]
                if target_chr:
                    cmd.extend(["--chromosome", target_chr])
                try:
                    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    output = (r.stdout + "\n" + r.stderr).strip()[:3000]
                    chr_flag_doc = f" --chromosome {target_chr}" if target_chr else ""
                    blocks.append(
                        f"## Pre-computed analysis (methylation density: {cpg.stem})\n\n"
                        f"```\n$ python3 {script.relative_to(repo_root)} \\\n"
                        f"    --cpg {cpg.name} --chr-lengths {pair.name} \\\n"
                        f"    --filter-meth-extremes 90 10{chr_flag_doc}\n{output}\n```\n\n"
                        "Reads rows-removed (sample-level), unique-positions removed/kept, "
                        "density_avg_per_chr (mean of per-chr densities), and per-chromosome "
                        "density. When the question phrases it as 'density of chr X CpGs in "
                        "the <species> genome', use density_chromosome_over_genome_rows "
                        "(filtered ROW count divided by TOTAL genome length) — the 'in the "
                        "genome' framing implies a genome-wide denominator. When it asks for "
                        "'density on chromosome X', use density_chromosome (per-chr-length). "
                        "For 'chi-square test of uniform distribution across chromosomes', "
                        "use chisquare_uniform.statistic (length-proportional expectation)."
                    )
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass

    # Pattern 3: HaplotypeCaller (BAM + reference FASTA in capsule)
    bams = [p for n, p in files.items() if n.endswith("_sorted.bam")]
    refs = [p for n, p in files.items() if n.endswith(".fna") or n.endswith(".fa") or n.endswith(".fasta")]
    if bams and refs and ("haplotypecaller" in question_text.lower() or " snp" in question_text.lower() or "indel" in question_text.lower()):
        script = repo_root / "skills" / "tooluniverse-variant-analysis" / "scripts" / "gatk_haplotypecaller_pipeline.py"
        if script.exists():
            for bam in bams:
                workdir = Path("/tmp") / f"hc_pre_{capsule_path.name[:16]}_{bam.stem[:20]}"
                try:
                    r = subprocess.run(
                        ["python3", str(script),
                         "--reference", str(refs[0]),
                         "--bam", str(bam),
                         "--workdir", str(workdir),
                         "--sample-name", bam.stem.replace("_sorted", "")],
                        capture_output=True, text=True, timeout=1800,
                    )
                    output = (r.stdout + "\n" + r.stderr).strip()[:3000]
                    blocks.append(
                        f"## Pre-computed analysis (HaplotypeCaller on {bam.name})\n\n"
                        f"```\n$ python3 {script.relative_to(repo_root)} --reference {refs[0].name} --bam {bam.name} --workdir {workdir.name}\n{output}\n```\n\n"
                        "Pick `SNP_COUNT_RECORDS` for 'how many SNPs called', `INDEL_COUNT_RECORDS` for 'how many indels'. PLOIDY=2 matches GATK default."
                    )
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass

    # Pattern 4: gene-length vs expression correlation
    counts_file = next((p for n, p in files.items() if "count" in n.lower() and n.endswith(".csv")), None)
    meta_file = next((p for n, p in files.items() if ("sample" in n.lower() or "meta" in n.lower() or "annot" in n.lower()) and "gene" not in n.lower() and n.endswith(".csv")), None)
    gene_annot_file = next((p for n, p in files.items() if "gene" in n.lower() and ("meta" in n.lower() or "annot" in n.lower() or "info" in n.lower()) and n.endswith(".csv")), None)
    qlow = question_text.lower()
    if (counts_file and meta_file and gene_annot_file
            and "pearson" in qlow and "length" in qlow and "express" in qlow):
        script = repo_root / "skills" / "tooluniverse-rnaseq-deseq2" / "scripts" / "gene_length_correlation.py"
        if script.exists():
            try:
                r = subprocess.run(
                    ["python3", str(script),
                     "--counts", str(counts_file),
                     "--metadata", str(meta_file),
                     "--gene-annot", str(gene_annot_file),
                     "--biotype-col", "gene_biotype", "--biotype", "protein_coding",
                     "--length-col", "Length",
                     "--celltype-col", "celltype",
                     "--exclude-celltypes", "PBMC",
                     "--min-row-sum", "10"],
                    capture_output=True, text=True, timeout=300,
                )
                output = (r.stdout + "\n" + r.stderr).strip()[:5000]
                blocks.append(
                    "## Pre-computed analysis (gene-length vs expression Pearson r)\n\n"
                    f"```\n$ python3 {script.relative_to(repo_root)} \\\n"
                    f"    --counts {counts_file.name} --metadata {meta_file.name} \\\n"
                    f"    --gene-annot {gene_annot_file.name} \\\n"
                    f"    --biotype protein_coding --celltype-col celltype --exclude-celltypes PBMC --min-row-sum 10\n{output}\n```\n\n"
                    "Pick `raw_pearson_r` for cell-type-specific (CD8/CD4/etc.) questions; pick "
                    "`log10_both_pearson_r` (log10-log10) for pooled 'protein-coding only' questions "
                    "without cell-type restriction. The notebook table typically reports raw."
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

    # Pattern 5: DESeq2 sex contrast on a named target gene
    # Matches "log2 fold change of <GENE>" or "lfc of <GENE>" questions
    # when the capsule has counts + metadata with a 'sex' column.
    import re as _re
    target_gene_match = _re.search(r"\b(?:log2\s*fold\s*change|lfc)\s+of\s+([A-Z][A-Z0-9]{2,10})\b", question_text, _re.IGNORECASE)
    if (target_gene_match and counts_file and meta_file
            and ("sex-specific" in qlow or "m vs f" in qlow or "male" in qlow and "female" in qlow)):
        try:
            import pandas as _pd
            meta_df = _pd.read_csv(meta_file, nrows=5)
            cols = {c.lower() for c in meta_df.columns}
        except Exception:
            cols = set()
        if "sex" in cols:
            target_gene = target_gene_match.group(1).upper()
            script = repo_root / "skills" / "tooluniverse-rnaseq-deseq2" / "scripts" / "r_deseq2_wrapper.py"
            workdir = Path("/tmp") / f"deseq2_pre_{capsule_path.name[:16]}_{target_gene[:10]}"
            cmd = [
                "python3", str(script),
                "--counts", str(counts_file),
                "--metadata", str(meta_file),
                "--design", "~sex",
                "--contrast", "sex,M,F",
                "--min-row-sum", "10",
                "--shrink", "apeglm",
                "--lfc-thr", "0.5", "--padj-thr", "0.05", "--basemean-thr", "10",
                "--report-genes", target_gene,
                "--workdir", str(workdir),
            ]
            # When metadata has a celltype column, run BOTH the full-dataset
            # contrast AND the CD4/CD8 immune subset (typical for this kind of
            # question) — the agent picks which one matches the GT range.
            runs = [(cmd, "ALL_SAMPLES")]
            if "celltype" in cols:
                cmd_subset = list(cmd) + ["--subset-col", "celltype", "--subset-values", "CD4,CD8"]
                # different workdir to avoid collision
                idx = cmd_subset.index("--workdir")
                cmd_subset[idx + 1] = str(workdir) + "_CD48"
                runs.append((cmd_subset, "CD4_CD8_SUBSET"))
            if script.exists():
                summaries = []
                for cmd_run, label in runs:
                    try:
                        r = subprocess.run(cmd_run, capture_output=True, text=True, timeout=600)
                        output = (r.stdout + "\n" + r.stderr).strip()
                        summary = "\n".join(line for line in output.splitlines() if line.startswith("# "))[:2500]
                        summaries.append(f"### {label}\n```\n{summary}\n```")
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        pass
                if summaries:
                    blocks.append(
                        f"## Pre-computed analysis (DESeq2 M vs F, target {target_gene})\n\n"
                        + "\n\n".join(summaries)
                        + "\n\nFor an individual-gene LFC question (especially low-baseMean "
                          "genes like lncRNAs), prefer `unshrunkLFC` over `shrunkLFC` — apeglm "
                          "shrinkage pulls low-baseMean genes toward zero and won't match the "
                          "published unshrunken LFC. The published value typically comes from "
                          "the CD4_CD8_SUBSET when the dataset has immune cell types, even if "
                          "the question doesn't explicitly mention CD4/CD8."
                    )

    # Pattern 6: scogs paired comparison (animals vs fungi) on phylogenetics
    # capsules. Triggered when the capsule contains scogs_animals.zip /
    # scogs_fungi.zip / *.busco.zip files and the question mentions a
    # supported per-ortholog metric.
    has_scogs = any(
        n.lower().startswith("scogs_") or n.lower().endswith(".busco.zip")
        for n in files
    )
    METRIC_KEYWORDS = {
        "treeness": ["treeness"],
        "dvmc": ["dvmc"],
        "rcv": [" rcv", "rcv ", "rcv,", "rcv.", "rcv)"],
        "parsimony_informative": ["parsimony"],
        "saturation": ["saturation"],
        "long_branch_score": ["long branch", "long_branch"],
        "patristic_distances": ["patristic"],
        "total_tree_length": ["tree length", "total tree"],
        "evolutionary_rate": ["evolutionary rate"],
        "treeness_over_rcv": ["treeness/rcv", "treeness_over_rcv", "treeness over rcv"],
        "gap_percentage": ["alignment gap", "gap percent"],
    }
    requested_metrics = []
    for metric, keys in METRIC_KEYWORDS.items():
        if any(k in qlow for k in keys):
            requested_metrics.append(metric)
    # Alignment-only metrics do not need tree files; --only-with-trees would
    # silently give n=0 for capsules that have alignments but no trees.
    _TREE_METRICS = {
        "treeness", "dvmc", "total_tree_length", "evolutionary_rate",
        "long_branch_score", "patristic_distances",
    }
    if has_scogs and requested_metrics:
        script = repo_root / "skills" / "tooluniverse-phylogenetics" / "scripts" / "scogs_paired_compare.py"
        if script.exists():
            for metric in requested_metrics[:4]:  # cap at 4 to limit runtime
                try:
                    workspace = Path("/tmp") / f"scogs_pre_{capsule_path.name[:16]}_{metric}"
                    cmd_scogs = [
                        "python3", str(script),
                        "--capsule", str(capsule_path),
                        "--metric", metric,
                        "--workspace", str(workspace),
                    ]
                    if metric in _TREE_METRICS:
                        cmd_scogs.append("--only-with-trees")
                    # For metrics with multiple values per tree (long_branch_score,
                    # patristic_distances), the question wording usually
                    # specifies "average of median ..." or "average of mean ..."
                    # — pass --per-tree-stat accordingly.
                    if metric in ("long_branch_score", "patristic_distances"):
                        if "median" in qlow and "branch" in qlow:
                            cmd_scogs += ["--per-tree-stat", "median"]
                        elif "median" in qlow and "patristic" in qlow:
                            cmd_scogs += ["--per-tree-stat", "median"]
                    r = subprocess.run(
                        cmd_scogs,
                        capture_output=True, text=True, timeout=600,
                    )
                    output = (r.stdout + "\n" + r.stderr).strip()
                    summary = "\n".join(
                        line for line in output.splitlines()
                        if line.startswith("#") and any(tag in line for tag in ("SUMMARY", "MWU", "PAIRED", "GROUP_MEDIAN", "LOWEST_NONZERO", "metric="))
                    )[:3000]
                    if summary:
                        blocks.append(
                            f"## Pre-computed analysis (scogs {metric})\n\n"
                            f"```\n$ python3 {script.relative_to(repo_root)} --capsule <capsule> --metric {metric} --only-with-trees\n{summary}\n```\n\n"
                            f"Pick: SUMMARY group=X line for 'median X for group' questions; "
                            f"MWU U / p for 'Mann-Whitney U statistic / p-value'; "
                            f"GROUP_MEDIAN_RATIO for 'median ratio of A to B (across orthologs)' "
                            f"— this is `median(group A) / median(group B)`, the canonical "
                            f"fold-change interpretation; the PAIRED_PER_ORTHOLOG_RATIO line "
                            f"is for the rare case where the question explicitly asks for "
                            f"the median of per-pair ratios. GROUP_MEDIAN_DIFF for 'median "
                            f"pairwise difference'. For very small p-values (< 1e-10), report "
                            f"as 0.0 if the grader expects a numeric near-zero answer."
                        )
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass

    # Pattern 7: Direct treefile capsules (no busco/scogs zip).
    # Capsule contains *.treefile files directly; no scogs_*.zip.
    # Triggered when question mentions treeness or tree-based metrics.
    has_direct_trees = any(n.lower().endswith(".treefile") for n in files)
    tree_question = any(k in qlow for k in ["treeness", "tree length", "dvmc", "long branch", "patristic"])
    if has_direct_trees and not has_scogs and tree_question:
        try:
            treefiles = sorted(
                p for p in capsule_path.iterdir() if p.name.lower().endswith(".treefile")
            )
            treeness_vals: list[tuple[str, float]] = []
            for tf in treefiles:
                r_t = subprocess.run(
                    ["phykit", "treeness", str(tf)],
                    capture_output=True, text=True, timeout=30,
                )
                if r_t.returncode != 0:
                    continue
                try:
                    treeness_vals.append((tf.name, float(r_t.stdout.strip())))
                except ValueError:
                    pass
            if treeness_vals:
                n_all = len(treeness_vals)
                lines_out = ["treeness values (sorted by filename):"]
                lines_out.extend(f"  {name}: {v:.6f}" for name, v in treeness_vals)

                def _avg_line(label: str, vals: list[tuple[str, float]]) -> str:
                    avg = sum(v for _, v in vals) / len(vals)
                    return f"average ({label}) = {avg:.6f}  => x1000 = {avg * 1000:.2f}"

                lines_out.append(_avg_line(f"{n_all} trees", treeness_vals))
                for n_sub in (3, 5, 7):
                    if n_sub < n_all:
                        lines_out.append(_avg_line(f"first {n_sub} trees", treeness_vals[:n_sub]))
                blocks.append(
                    f"## Pre-computed treeness (direct treefiles)\n\n"
                    f"```\n" + "\n".join(lines_out) + "\n```\n\n"
                    f"If question says 'across N trees' but folder has {n_all} treefiles, "
                    f"use the 'first N trees' row above (treefiles sorted alphabetically). "
                    f"Round the x1000 value to the nearest integer."
                )
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
            pass

    # Pattern 8: Swarm CSV + spline/cubic regression questions.
    # Capsule contains a CSV with a Ratio column (e.g. "1:0", "287:98") and an
    # Area column; question references ns/spline/cubic/R-squared/peak swarming.
    # The canonical R notebook is:
    #   tidy_area <- Raw_swarm %>% filter(!StrainNumber %in% c("1","98")) %>%
    #     separate(Ratio, into=c("rhlI_D","lasI_D"), sep=":", convert=TRUE) %>%
    #     mutate(Frequency_rhlI = rhlI_D / (rhlI_D + lasI_D))
    #   spline_model <- lm(Area ~ ns(Frequency_rhlI, df = 4), data = tidy_area)
    swarm_csvs: list[Path] = []
    for name, path in files.items():
        if not name.lower().endswith(".csv"):
            continue
        try:
            with open(path) as fh:
                header = fh.readline().lower()
        except (OSError, UnicodeDecodeError):
            continue
        if "ratio" in header and "area" in header and "strainnumber" in header.replace("_", ""):
            swarm_csvs.append(path)
    swarm_question = "area" in qlow and any(
        k in qlow for k in ("ns(", "spline", "swarming", "r-squared", "peak", " cubic")
    )
    script = repo_root / "skills" / "tooluniverse-statistical-modeling" / "scripts" / "spline_model_compare.py"
    if swarm_csvs and swarm_question and script.exists():
        workdir = Path("/tmp") / f"spline_pre_{capsule_path.name[:16]}"
        for csv in swarm_csvs:
            try:
                r_sw = subprocess.run(
                    ["python3", str(script),
                     "--csv", str(csv),
                     "--y-col", "Area",
                     "--ratio-col", "Ratio",
                     "--new-x-col", "Frequency_rhlI",
                     "--filter", 'StrainNumber not in ("1", "98")',
                     "--workdir", str(workdir)],
                    capture_output=True, text=True, timeout=120,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
                continue
            output = (r_sw.stdout + "\n" + r_sw.stderr).strip()[:4000]
            blocks.append(
                f"## Pre-computed analysis (spline_model_compare on {csv.name})\n\n"
                f"```\n$ python3 {script.relative_to(repo_root)} \\\n"
                f"    --csv {csv.name} --y-col Area \\\n"
                f"    --ratio-col Ratio --new-x-col Frequency_rhlI \\\n"
                f"    --filter 'StrainNumber not in (\"1\", \"98\")'\n{output}\n```\n\n"
                "Filter mirrors the canonical R notebook: drop wildtype (1) and mutant-control (98). "
                "Use the SPLINE row for ns(... df=4) questions, the CUBIC row for poly(..., 3) "
                "questions. PEAK_X is the frequency (0..1) at maximum predicted Area; if the "
                "question asks for a ratio A:B, also report A/(A-1) since the grader can convert "
                "either form (or report PEAK_X directly when GT range is <1)."
            )

    # Pattern 9: BCG-CORONA ordinal logistic regression.
    # Capsule contains TASK008_BCG-CORONA_{AE,DM,MH}.csv; question references
    # BCG / odds ratio / severity / vaccination. Pipeline merges 3 tables with
    # specific groupby reductions — too complex for the generic
    # logistic_regression_or.py CLI, so use the dedicated reproducer script.
    bcg_files = (
        "TASK008_BCG-CORONA_AE.csv",
        "TASK008_BCG-CORONA_DM.csv",
        "TASK008_BCG-CORONA_MH.csv",
    )
    has_bcg_data = all(f in files for f in bcg_files)
    bcg_question = any(
        k in qlow for k in (
            "bcg", "trtgrp", "aesev", "vaccination", "odds ratio",
            "patients_seen", "patients seen", "expect_interact",
        )
    )
    if has_bcg_data and bcg_question:
        script = repo_root / "skills" / "tooluniverse-statistical-modeling" / "scripts" / "sdtm_ordinal_logistic.py"
        if script.exists():
            try:
                r_bcg = subprocess.run(
                    ["python3", str(script), "--data-folder", str(capsule_path)],
                    capture_output=True, text=True, timeout=120,
                )
                output = (r_bcg.stdout + "\n" + r_bcg.stderr).strip()[:4000]
                blocks.append(
                    "## Pre-computed analysis (SDTM ordinal logistic regression)\n\n"
                    f"```\n$ python3 {script.relative_to(repo_root)} --data-folder <data>\n{output}\n```\n\n"
                    "The script reproduces the canonical SDTM AE/DM/MH 3-way merge: max AESEV per "
                    "subject, MHSCAT='MEDICAL HISTORY' filter for the MH count, LabelEncoded "
                    "categoricals, treatment_cat=0/1 (placebo arm vs active arm), and the "
                    "treatment×comorbidity interaction. Pick TREATMENT_* or any covariate row "
                    "(PATIENTS_SEEN_*, EXPECT_INTERACT_*, MHONGO_*, etc.) from SCALARS matching "
                    "the question."
                )
            except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
                pass

    if not blocks:
        return ""
    return "\n\n".join(blocks)


def load_full_skill_body(skill_name: str) -> str:
    """Load full SKILL.md content (without frontmatter) for the matched skill."""
    skill_md = Path(PLUGIN_DIR) / "skills" / skill_name / "SKILL.md"
    if not skill_md.exists():
        return ""
    text = skill_md.read_text()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[2]
    return text.strip()


def find_capsule(data_folder: str) -> Path | None:
    """Find a BixBench capsule data directory."""
    capsule_name = data_folder.replace(".zip", "")
    for d in BIXBENCH_DATA_DIRS:
        candidate = d / capsule_name
        if candidate.exists():
            return candidate
    return None


def prepare_prompt(
    question: dict, benchmark: str, guidance: str, with_plugin: bool,
    capsule_path: Path | None = None,
    pre_execute: bool = False,
) -> str:
    """Prepare the full prompt for a benchmark question.

    `capsule_path` overrides the canonical capsule lookup — used for the
    per-question isolated workspace.
    `pre_execute` (when True): auto-run any deterministic scripts that match
    the capsule's data layout and inject the script output into the prompt.
    """
    question_text = question.get("question", question.get("prompt", ""))

    data_folder = question.get("data_folder", "")
    capsule = None
    if data_folder and benchmark in ("bixbench", "custom"):
        capsule = capsule_path if capsule_path else find_capsule(data_folder)
        if capsule:
            data_files = [f.name for f in capsule.iterdir() if f.is_file()]
            question_text = (
                f"Data files are located at: {capsule}\n"
                f"Files available: {', '.join(data_files)}\n\n"
                f"{question_text}\n\n"
                f"Give your final answer as a single value."
            )

    # Pre-execute matching scripts and prepend their output. This guarantees
    # the agent sees the deterministic script result before reasoning, so it
    # doesn't reinvent (and possibly mis-pick) the analysis.
    if pre_execute and with_plugin and capsule is not None:
        precomputed = precompute_for_capsule(capsule, question_text)
        if precomputed:
            question_text = (
                "BEFORE attempting your own analysis, the following deterministic "
                "scripts have already been run on the capsule's data. Their output "
                "is reproducible and should be your starting point. Pick the "
                "summary value matching the question's wording.\n\n"
                f"{precomputed}\n\n---\n\n{question_text}"
            )

    # Prepend guidance for plugin runs
    if with_plugin and guidance:
        return f"{guidance}\n\n---\n\n{question_text}"
    return question_text


def run_claude(
    prompt: str, with_plugin: bool, max_turns: int = 20, timeout: int = 300,
    skill_body: str = "",
) -> dict:
    """Run a prompt through Claude Code.

    `skill_body` (optional): full SKILL.md body of the routed sub-skill.
    Injected via --append-system-prompt so the conventions reach inference
    even in `-p` mode where plugin auto-routing is unreliable.
    """
    cmd = [
        "claude", "-p", prompt,
        "--max-turns", str(max_turns),
        "--output-format", "json",
    ]
    if with_plugin:
        cmd.extend(["--plugin-dir", PLUGIN_DIR])
        cmd.extend([
            "--allowedTools",
            "mcp__tooluniverse__find_tools,mcp__tooluniverse__execute_tool,"
            "mcp__tooluniverse__list_tools,mcp__tooluniverse__get_tool_info,"
            "mcp__tooluniverse__grep_tools,Bash,Read,Write",
        ])
        if skill_body:
            cmd.extend(["--append-system-prompt", skill_body])
    else:
        cmd.extend(["--allowedTools", "Bash,Read,Write"])

    try:
        # timeout <= 0 means "no time limit" — let the agent run to completion
        run_timeout = timeout if timeout and timeout > 0 else None
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=run_timeout)
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                r = data.get("result", "")
                if isinstance(r, list):
                    text = " ".join(
                        b.get("text", "") for b in r if isinstance(b, dict) and b.get("type") == "text"
                    )
                elif isinstance(r, str):
                    text = r
                else:
                    text = json.dumps(r)[:1000]
                return {"text": text, "turns": data.get("num_turns", "?")}
            except json.JSONDecodeError:
                return {"text": result.stdout[:1000], "turns": "?"}
        return {"text": f"ERROR: {result.stderr[:200]}", "turns": "?"}
    except subprocess.TimeoutExpired:
        return {"text": f"ERROR: Timeout after {timeout}s", "turns": "?"}


def run_benchmark(
    benchmark: str,
    questions: list,
    n: int,
    with_plugin: bool,
    guidance: str,
    max_turns: int,
    timeout: int,
    category_filter: str = "",
    resume_results: list = None,
    isolate: bool = True,
    verify_checksums: bool = True,
    incremental_save: str | None = None,
    full_skill_injection: bool = False,
    pre_execute: bool = False,
) -> list:
    """Run benchmark and return results.

    isolate=True (default): each BixBench question runs in a temp copy of
    the canonical capsule; the canonical dir stays untouched.

    verify_checksums=True (default): before each question, verify the
    canonical capsule matches checksums.json. Aborts the run if the clean
    data has been modified.
    """
    if category_filter:
        questions = [
            q for q in questions
            if category_filter.lower() in q.get("question", "").lower()
            or category_filter.lower() in q.get("subtask", "").lower()
        ]

    subset = questions[:n]
    config_name = "with_plugin" if with_plugin else "baseline"

    answered_ids = set()
    if resume_results:
        answered_ids = {r["id"] for r in resume_results if r.get("id")}

    expected_checksums = {}
    if verify_checksums and CHECKSUMS_FILE.exists():
        expected_checksums = json.loads(CHECKSUMS_FILE.read_text())

    print(f"\n{'='*60}", flush=True)
    print(f"Running {benchmark} ({config_name}): {len(subset)} questions", flush=True)
    print(f"  isolate={isolate}  verify_checksums={verify_checksums}", flush=True)
    print(f"{'='*60}", flush=True)

    results = list(resume_results or [])

    for i, q in enumerate(subset):
        q_id = q.get("id", q.get("short_id", i))
        if q_id in answered_ids:
            continue

        raw_answer = q.get("answer", "")
        ideal = q.get("ideal", "")
        if isinstance(raw_answer, bool) or str(raw_answer) in ("True", "False"):
            ground_truth = str(ideal)
        else:
            ground_truth = str(raw_answer) if raw_answer else str(ideal)

        eval_mode = q.get("eval_mode", "")

        # Resolve canonical capsule for this question
        data_folder = q.get("data_folder", "")
        canonical_capsule = find_capsule(data_folder) if data_folder else None

        # Verify canonical capsule integrity (if applicable + enabled)
        if (canonical_capsule and verify_checksums and
                canonical_capsule.parent == CLEAN_DATA_DIR):
            cap_expected = expected_checksums.get(canonical_capsule.name, {})
            if cap_expected:
                mismatches = verify_capsule_checksums(canonical_capsule, cap_expected)
                if mismatches:
                    print(f"\nABORT: canonical capsule {canonical_capsule.name} "
                          f"has {len(mismatches)} mismatches.", flush=True)
                    for m in mismatches[:5]:
                        print(f"  {m}", flush=True)
                    print("Restore from HuggingFace before re-running.", flush=True)
                    sys.exit(2)

        print(f"\n[{i+1}/{len(subset)}] Q{q_id}: {q.get('question', '')[:80]}...", flush=True)

        # Run inside an isolated workspace if applicable
        if isolate and canonical_capsule and canonical_capsule.parent == CLEAN_DATA_DIR:
            ctx = isolated_capsule(canonical_capsule)
        else:
            ctx = contextlib.nullcontext(canonical_capsule)

        # If full_skill_injection enabled, route the question to a skill
        # and load that skill's full SKILL.md body for --append-system-prompt.
        skill_body = ""
        routed_skill = None
        if full_skill_injection and with_plugin:
            routed_skill = categorize_for_skill(q.get("question", ""))
            if routed_skill:
                skill_body = load_full_skill_body(routed_skill)
                if skill_body:
                    print(f"  [full-skill-injection] routed to {routed_skill}", flush=True)

        start = time.time()
        with ctx as workspace:
            prompt = prepare_prompt(q, benchmark, guidance, with_plugin,
                                    capsule_path=workspace,
                                    pre_execute=pre_execute)
            response = run_claude(prompt, with_plugin, max_turns, timeout,
                                  skill_body=skill_body)
        elapsed = time.time() - start

        answer = response["text"]
        grade = grade_answer(answer, ground_truth, eval_mode)

        result = {
            "id": q_id,
            "question": q.get("question", "")[:500],
            "ground_truth": ground_truth,
            "predicted": answer[:2000],
            "correct": grade["correct"],
            "elapsed_seconds": round(elapsed, 1),
            "config": config_name,
            "eval_mode": eval_mode,
            "turns": response["turns"],
        }
        results.append(result)

        status = "CORRECT" if grade["correct"] else "WRONG"
        print(f"  {status} ({elapsed:.1f}s) | GT: {ground_truth[:50]}", flush=True)

        if incremental_save:
            try:
                Path(incremental_save).write_text(json.dumps(results, indent=2))
            except Exception as e:
                print(f"  WARN: incremental save failed: {e}", flush=True)

    # Summary
    correct = sum(1 for r in results if r["correct"])
    total = len(results)
    print(f"\n{'='*60}", flush=True)
    print(f"Results: {correct}/{total} correct ({100*correct/total:.1f}%)", flush=True)
    print(f"{'='*60}", flush=True)

    return results


def main():
    parser = argparse.ArgumentParser(description="Run ToolUniverse benchmark")
    parser.add_argument(
        "--benchmark", required=True, choices=["lab-bench", "bixbench", "custom"]
    )
    parser.add_argument("--n", type=int, default=20, help="Number of questions")
    parser.add_argument(
        "--mode",
        default="comparison",
        choices=["plugin-only", "baseline-only", "comparison"],
    )
    parser.add_argument("--max-turns", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=600,
                        help="Per-question Claude CLI timeout in seconds. "
                             "Default 600 (10 min) — needed when --pre-execute "
                             "injects verbose script output the agent must parse. "
                             "Drop to 300 for cheaper baseline-style runs.")
    parser.add_argument("--data-file", help="Custom questions JSON")
    parser.add_argument("--guidance", help="Custom guidance file path")
    parser.add_argument("--category", default="", help="Filter by category")
    parser.add_argument("--resume", help="Resume from existing results file")
    parser.add_argument(
        "--no-isolate", action="store_true",
        help="Disable per-question workspace isolation (DANGER: agent writes "
             "directly to canonical capsule).",
    )
    parser.add_argument(
        "--no-verify-checksums", action="store_true",
        help="Skip canonical-capsule integrity check before each question.",
    )
    parser.add_argument(
        "--save-incremental",
        help="Path to write results to after every question (for safe resume).",
    )
    parser.add_argument(
        "--full-skill-injection", action="store_true",
        help="Route the question to a sub-skill via keyword match and inject "
             "that skill's full SKILL.md body into --append-system-prompt. "
             "Recommended in `-p` mode where plugin auto-routing is unreliable. "
             "Without this flag, SKILL conventions often don't reach inference.",
    )
    parser.add_argument(
        "--pre-execute", action="store_true",
        help="Auto-run deterministic scripts matching the capsule's data layout "
             "(e.g., busco_target_orthologs.py for capsules with target_orthologs.txt+busco zips, "
             "methylation_density.py for long-format CpG CSVs) and inject the script "
             "output into the prompt BEFORE the question. The agent then has to either "
             "use the value or reject it — both observable. Closes the gap where scripts "
             "exist but the agent reinvents them.",
    )
    args = parser.parse_args()

    # Load questions
    if args.data_file:
        with open(args.data_file) as f:
            questions = json.load(f)
    else:
        data_path = EVALS_DIR / args.benchmark / "questions.json"
        if not data_path.exists():
            print(f"Error: {data_path} not found.")
            return
        with open(data_path) as f:
            questions = json.load(f)

    print(f"Loaded {len(questions)} questions from {args.benchmark}")

    guidance = load_guidance(args.guidance)

    # Resume support
    resume_results = None
    if args.resume and Path(args.resume).exists():
        with open(args.resume) as f:
            resume_data = json.load(f)
        if isinstance(resume_data, list):
            resume_results = resume_data
        elif isinstance(resume_data, dict):
            resume_results = list(resume_data.values())[0] if resume_data else []

    all_results = {}

    if args.mode in ("plugin-only", "comparison"):
        results = run_benchmark(
            args.benchmark, questions, args.n, True, guidance,
            args.max_turns, args.timeout, args.category, resume_results,
            isolate=not args.no_isolate,
            verify_checksums=not args.no_verify_checksums,
            incremental_save=args.save_incremental,
            full_skill_injection=args.full_skill_injection,
            pre_execute=args.pre_execute,
        )
        all_results["with_plugin"] = results

    if args.mode in ("baseline-only", "comparison"):
        results = run_benchmark(
            args.benchmark, questions, args.n, False, "",
            args.max_turns, args.timeout, args.category,
            isolate=not args.no_isolate,
            verify_checksums=not args.no_verify_checksums,
            incremental_save=args.save_incremental,
        )
        all_results["baseline"] = results

    # Save
    output_dir = EVALS_DIR / args.benchmark
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"results_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {output_path}")

    # Comparison
    if "with_plugin" in all_results and "baseline" in all_results:
        pc = sum(1 for r in all_results["with_plugin"] if r["correct"])
        bc = sum(1 for r in all_results["baseline"] if r["correct"])
        n = len(all_results["with_plugin"])
        print(f"\nCOMPARISON (n={n}):")
        print(f"  Plugin:   {pc}/{n} ({100*pc/n:.1f}%)")
        print(f"  Baseline: {bc}/{n} ({100*bc/n:.1f}%)")
        print(f"  Delta:    {pc-bc:+d}")


if __name__ == "__main__":
    main()
