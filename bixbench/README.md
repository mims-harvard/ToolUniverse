# BixBench Testing for ToolUniverse

Testing infrastructure for validating ToolUniverse skills on BixBench computational biology questions.

---

## Folder Structure

```
bixbench/
├── README.md                      # This file
├── test_single_question.py        # Main test script
├── test_with_subagent.py          # Test using Claude subagent
├── requirements.txt               # Python dependencies
├── data/                          # Downloaded capsule data (gitignored)
├── results/                       # Test results and logs
└── scripts/                       # Helper utilities
```

---

## Quick Start

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Authenticate with HuggingFace
huggingface-cli login

# Test a single question
python test_single_question.py bix-13-q2
```

---

## How Subagent Testing Works

### Question: "How would the subagent run? What are the inputs?"

### Answer: Two Approaches

#### **Approach A: Direct Skill Invocation** (Programmatic)

The skill receives structured data and returns a structured answer:

```python
# Input to skill
skill_input = {
    "data_directory": "./bixbench/data/CapsuleFolder-xxx/",
    "question": "How many genes are uniquely differentially expressed in JBX98?",
    "hypothesis": "Knocking out rhlI impacts downstream expression...",
    "context": {
        "comparison": "JBX98 vs JBX1",
        "method": "DESeq2",
        "fdr_threshold": 0.05,
    }
}

# Call skill
result = tooluniverse.call_skill("tooluniverse-rnaseq-deseq2", skill_input)

# Output from skill
{
    "answer": "166",
    "details": {
        "total_genes": 4387,
        "deg_jbx98": 188,
        "deg_jbx97": 210,
        "deg_jbx99": 166,
        "unique_jbx98": 166,
    },
    "files_generated": ["deseq2_results.csv", "volcano_plot.png"]
}
```

**Pros**: Fast, deterministic, easy to debug
**Cons**: Skills need to parse question text to extract parameters

---

#### **Approach B: Subagent with Natural Language** (Agentic)

A Claude subagent reads the question and uses skills interactively:

```python
# Launch subagent
agent = Task(
    subagent_type="general-purpose",
    prompt=f"""
You are a computational biologist testing tool capabilities.

**Question**: {question["question"]}
**Hypothesis**: {question["hypothesis"]}
**Result Context**: {question["result"]}

**Data Files Available**:
{list(data_dir.iterdir())}

**Your Task**:
1. Analyze the question and determine what analysis is needed
2. Use /tooluniverse skill to route to appropriate specialized skill
3. Provide the data files and parameters to the skill
4. Extract the final numerical answer
5. Return ONLY the answer in this format:
   ANSWER: [number]

**Available Skills**:
- /tooluniverse-rnaseq-deseq2 - For differential expression
- /tooluniverse-variant-analysis - For VCF analysis
- /tooluniverse-single-cell - For scRNA-seq
- ... (other skills)

Begin your analysis.
""")

# Agent output
agent_response = """
Let me analyze this step by step:

1. The question asks about genes uniquely differentially expressed in JBX98
2. This requires DESeq2 differential expression analysis
3. I need to compare JBX98 vs JBX1 and exclude genes also in JBX97/JBX99

I'll use the RNA-seq DESeq2 skill:
<uses /tooluniverse-rnaseq-deseq2>
...
<skill returns results>

The unique DEGs in JBX98 are: 166 genes

ANSWER: 166
"""

# Parse answer
answer = extract_answer(agent_response)  # "166"
```

**Pros**: Natural, tests real-world usage, agent interprets question
**Cons**: Slower, non-deterministic, costs API calls

---

## Detailed Input/Output Flow

### What the Subagent Receives (Initial Prompt)

```
SYSTEM: You are testing ToolUniverse computational biology skills

INPUT PROVIDED:
1. question["question"]:
   "Using DESeq2 to conduct differential expression analysis relative to
    strain JBX1, how many genes are uniquely and statistically significantly
    differentially expressed in JBX98 but not in either JBX97 or JBX99?"

2. question["hypothesis"]:
   "Knocking out either rhlI or lasI impacts the downstream expression of
    dozens of genes which may be involved in mediating the observed division
    of labor."

3. question["result"]:
   "DEseq was used to determine which genes were differentially expressed
    (FDR < 0.05) for ΔrhlI, ΔlasI and ΔlasIΔrhlI. The results were visualized
    in a Venn Diagram..."

4. data_directory:
   "./bixbench/data/CapsuleFolder-1d54e4a7-8b0f-4224-bd31-efcfded0d46c/"

   Contains files:
   - counts.csv              # Gene count matrix
   - metadata.csv            # Sample information
   - gene_annotations.csv    # Gene names/IDs
   - design_matrix.csv       # Experimental design

5. expected_answer (hidden from agent):
   "166"

6. eval_mode (hidden from agent):
   "str_verifier"

TASK:
Use /tooluniverse skill to answer the question using the provided data.
Return your answer in the format: ANSWER: [your answer]
```

---

### What the Skill Receives (from Subagent)

When the subagent calls `/tooluniverse-rnaseq-deseq2`:

```
INPUT TO SKILL:
- Routed automatically to /tooluniverse-rnaseq-deseq2 (via router)
- Subagent provides:
  * Data file paths
  * Analysis parameters extracted from question
  * Context about what comparison to make

SKILL PROMPT (what skill sees):
"""
Analyze differential gene expression using DESeq2.

Data: ./bixbench/data/CapsuleFolder-xxx/counts.csv
Design: Compare JBX98 vs JBX1
Method: PyDESeq2 with FDR < 0.05
Additional: Also run for JBX97 and JBX99, then find unique to JBX98

Use the guidance in /tooluniverse-rnaseq-deseq2 to:
1. Load count matrix
2. Run DESeq2 for each comparison
3. Filter by FDR < 0.05
4. Find genes unique to JBX98
"""
```

---

### What the Skill Returns (to Subagent)

```
OUTPUT FROM SKILL:
{
  "analysis_complete": true,
  "comparisons": {
    "JBX98_vs_JBX1": {
      "total_deg": 188,
      "upregulated": 95,
      "downregulated": 93
    },
    "JBX97_vs_JBX1": {
      "total_deg": 210,
      "upregulated": 108,
      "downregulated": 102
    },
    "JBX99_vs_JBX1": {
      "total_deg": 166,
      "upregulated": 85,
      "downregulated": 81
    }
  },
  "unique_to_JBX98": 166,
  "unique_genes": ["gene1", "gene2", ...],
  "files_generated": [
    "./results/deseq2_jbx98.csv",
    "./results/deseq2_jbx97.csv",
    "./results/deseq2_jbx99.csv",
    "./results/venn_diagram.png"
  ]
}
```

---

### What the Subagent Returns (Final Answer)

```
SUBAGENT FINAL OUTPUT:
"""
I've completed the differential expression analysis:

1. Loaded count matrix with 4,387 genes across all samples
2. Ran PyDESeq2 for three comparisons:
   - JBX98 vs JBX1: 188 DEGs
   - JBX97 vs JBX1: 210 DEGs
   - JBX99 vs JBX1: 166 DEGs

3. Identified genes unique to JBX98 (not in JBX97 or JBX99): 166 genes

These results match the hypothesis that rhlI/lasI knockouts affect
downstream gene expression in distinct patterns.

ANSWER: 166
"""
```

---

### Evaluation

```python
# Extract answer
agent_answer = "166"
expected_answer = "166"
eval_mode = "str_verifier"

# Compare
correct = (agent_answer.strip() == expected_answer.strip())
# Result: ✅ PASS
```

---

## Input Format Comparison

### BixBench's Original Approach (Docker + Notebook)

```python
# Agent has access to three tools:
agent.tools = [
    "edit_cell",      # Modify notebook cells
    "list_workdir",   # Navigate file system
    "submit_answer"   # Submit final answer
]

# Agent workflow:
1. list_workdir() → see files
2. edit_cell("import pandas as pd; df = pd.read_csv('counts.csv')")
3. edit_cell("# Run DESeq2 analysis...")
4. submit_answer("166")
```

**Limitations**:
- Requires full Jupyter notebook environment
- Agent must write analysis code from scratch
- No reusable skill infrastructure

---

### ToolUniverse Approach (Skills)

```python
# Agent has access to specialized skills:
agent.skills = [
    "/tooluniverse",                # Router
    "/tooluniverse-rnaseq-deseq2", # DESeq2 expert
    "/tooluniverse-variant-analysis",
    # ... 50+ specialized skills
]

# Agent workflow:
1. Invoke /tooluniverse with question
2. Router directs to /tooluniverse-rnaseq-deseq2
3. Skill provides workflow guidance + tool access
4. Agent uses skill's curated tools (GEO, PyDESeq2, etc.)
5. Return structured result
```

**Advantages**:
- Reusable domain expertise (skills)
- Access to 1,546 scientific tools
- Structured workflows (not ad-hoc coding)
- No environment setup (uses APIs)

---

## Key Difference: Skills vs Raw Code

### BixBench Tests: "Can agent write Python/R from scratch?"
- Agent must generate analysis code
- Tests coding ability + domain knowledge
- Requires understanding of libraries (DESeq2, scanpy, etc.)

### ToolUniverse Tests: "Can agent use expert tools effectively?"
- Agent uses pre-built skills with domain expertise
- Tests tool selection + workflow orchestration
- Skills provide best practices built-in

**Both are valuable** - they test different capabilities:
- BixBench: Code generation for computational biology
- ToolUniverse: Scientific tool usage + research workflows

---

## Testing Modes

### Mode 1: Direct Testing (Fast)
```bash
python test_single_question.py bix-13-q2
```
- Programmatic: Call skills directly
- Fast: <1 minute per question
- Use for: Development, debugging, validation

### Mode 2: Subagent Testing (Realistic)
```bash
python test_with_subagent.py bix-13-q2
```
- Agentic: Subagent interprets question
- Slow: 2-5 minutes per question
- Use for: Real-world capability testing

### Mode 3: Batch Testing
```bash
python test_batch.py --category differential_expression
```
- Test all questions in a category
- Generates report with pass rate
- Use for: Comprehensive evaluation

---

## Expected Workflow for a Subagent

```
1. RECEIVE QUESTION
   ↓
   Input: Question text, hypothesis, data files

2. UNDERSTAND TASK
   ↓
   Agent: "This is a differential expression question"
   Agent: "I need to compare strains using DESeq2"

3. ROUTE TO SKILL
   ↓
   Agent: Invoke /tooluniverse
   Router: Directs to /tooluniverse-rnaseq-deseq2

4. USE SKILL GUIDANCE
   ↓
   Skill provides: Workflow steps, tool recommendations
   Agent: Follows skill's PyDESeq2 workflow

5. EXECUTE ANALYSIS
   ↓
   Agent: Loads data using skill's helpers
   Agent: Runs analysis following skill's patterns
   Agent: Generates results

6. EXTRACT ANSWER
   ↓
   Agent: Parses results to find answer
   Agent: Formats as requested (number, range, etc.)

7. RETURN ANSWER
   ↓
   Output: "ANSWER: 166"
```

---

## Implementation Status

- [x] Folder structure created
- [ ] `test_single_question.py` - Direct testing script
- [ ] `test_with_subagent.py` - Agentic testing script
- [ ] `requirements.txt` - Dependencies list
- [ ] `scripts/evaluate.py` - Batch evaluation
- [ ] `results/` - Test results storage

---

## Next Steps

1. Implement `test_single_question.py` (direct testing)
2. Implement `test_with_subagent.py` (agentic testing)
3. Test on bix-13-q2 to validate workflow
4. Document findings and skill improvements needed

---

**Last Updated**: 2026-02-17
