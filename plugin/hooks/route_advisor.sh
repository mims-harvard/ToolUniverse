#!/usr/bin/env bash
# UserPromptSubmit hook for ToolUniverse plugin.
#
# Outputs a routing instruction IFF the user's prompt looks like a research /
# data-analysis question. For trivial chat / coding / general questions, the
# hook is a no-op so the agent isn't forced to load 25K tokens of skill bodies
# it doesn't need.
#
# Detection signals (any of these triggers the routing instruction):
#   1. Data-file extensions in the prompt (.csv, .vcf, .h5ad, etc.)
#   2. Scientific-analysis keywords (DESeq2, GWAS, enrichment, etc.)
#   3. Path templates indicating a benchmark/data folder
#
# Stays silent on prompts that contain none of these.
#
# stdin format: JSON object with a "prompt" field (Claude Code passes the
# user's message wrapped in a JSON event payload).

# Extract .prompt from the JSON event. Fall back to raw stdin if jq is missing.
if command -v jq >/dev/null 2>&1; then
    prompt=$(jq -r '.prompt // empty' 2>/dev/null)
else
    prompt=$(python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('prompt',''))" 2>/dev/null)
fi

# Empty prompt → silent
[ -z "$prompt" ] && exit 0

file_signal='\.(csv|vcf|fasta|fa|faa|fastq|fq|h5ad|tsv|xlsx|bam|treefile|rds|tif|ipynb)( |$|/|"|'\'')'

domain_signal='differential expression|DESeq2|RNA-seq|enrichGO|enrichKEGG|enrichment analysis|variant calling|GWAS|phylogen|chi-square|ANOVA|ordinal|logistic regression|odds ratio|p-value|adjusted p|p\.adj|log2FC|fold change|methylation|MAGeCK|microscopy|colony|proteomics|mass spec|spatial transcriptomics|single-cell|scRNA|FASTQ|trimmomatic|samtools|coding variant|VAF|allele frequency'

path_template='[Dd]ata files? (are )?located at|[Dd]ata folder:|capsule.{1,30}folder|/[A-Za-z][A-Za-z0-9_-]{0,30}/data/'

if echo "$prompt" | grep -qiE "$file_signal|$domain_signal|$path_template"; then
    cat <<'EOF'
For research / data-analysis / biology / chemistry / medicine questions, run BOTH of these tool calls before ANY Bash/Read/Grep on the data:

  Skill(skill="tooluniverse")                                  # load routing table
  Skill(skill="tooluniverse-<picked-from-routing-table>")      # load sub-skill body

Why both: the sub-skill body contains RULE ZERO (read the executed notebook, do NOT reimplement), exact column names, R-vs-Python tool choices, and outlier-sample exclusions. Skipping the sub-skill = wrong answer. After Step 2 completes, then run data tools.
EOF
fi
