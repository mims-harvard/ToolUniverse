# Output Formatting Guide

Match question's requested format exactly.

## Numeric Precision

### Decimal Places

```python
# "rounded to 2 decimal points"
answer = round(value, 2)

# "rounded to 4 decimal points"
answer = round(value, 4)

# "rounded to 1 decimal place"
answer = round(value, 1)
```

### Scientific Notation

```python
# "in scientific notation"
answer = f"{value:.2E}"  # e.g., "1.23E-05"

# With specific precision
answer = f"{value:.3E}"  # e.g., "1.234E-05"

# Standard form (lowercase e)
answer = f"{value:.2e}"  # e.g., "1.23e-05"
```

### Integer Counts

```python
# "how many genes"
answer = int(len(sig_genes))  # No decimals

# Ensure integer type
answer = len(sig_genes)  # Already int from len()
```

## Percentages

```python
# "as a percentage"
answer = f"{value * 100:.1f}%"  # e.g., "15.3%"

# Without percent sign
answer = round(value * 100, 1)  # e.g., 15.3

# "as a percentage rounded to 2 decimal points"
answer = round(value * 100, 2)  # e.g., 15.32
```

## Ratios and Fractions

```python
# "as a ratio X:Y"
answer = f"{x}:{y}"  # e.g., "3:1"

# "as a fraction"
answer = f"{numerator}/{denominator}"  # e.g., "11/42"
```

## Ranges

```python
# For range_verifier evaluation mode
# Expected: (700, 1000)
# Your answer: 842  -> PASS (within range)
answer = 842

# Confidence intervals
ci_low, ci_high = proportion_confint(n_sig, n_total, method='wilson')
answer = (round(ci_low, 2), round(ci_high, 2))  # e.g., (0.15, 0.25)
```

## Lists

```python
# "list the top 5 genes"
answer = results.sort_values('padj').head(5).index.tolist()

# Comma-separated string
answer = ", ".join(gene_list)  # e.g., "TP53, BRCA1, EGFR"
```

## Boolean/Categorical

```python
# "Yes" or "No"
answer = "Yes" if condition else "No"

# "increases" or "decreases"
if n_clean > n_all:
    answer = "Increases the number of differentially expressed genes"
else:
    answer = "Decreases the number of differentially expressed genes"
```

## Tables

```python
# DataFrame subset
answer = results[['log2FoldChange', 'padj']].head(10)

# Markdown table
def to_markdown_table(df):
    """Convert DataFrame to markdown table."""
    lines = []
    lines.append("| " + " | ".join(df.columns) + " |")
    lines.append("| " + " | ".join(["---"] * len(df.columns)) + " |")
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)
```

## Common BixBench Formats

### Count (integer)

```python
# "How many genes..."
answer = len(sig_genes)
```

### P-value (4 decimals)

```python
# "What is the adjusted p-value..."
answer = round(pathway.iloc[0]['Adjusted P-value'], 4)
```

### Log2FC (2 decimals)

```python
# "What is the log2 fold change..."
answer = round(results.loc['TP53', 'log2FoldChange'], 2)
```

### Percentage (1 decimal)

```python
# "What percentage of..."
percentage = len(overlap) / len(degs_A) * 100
answer = round(percentage, 1)
```

### Scientific notation (p-values)

```python
# Very small p-values
answer = f"{pvalue:.2E}"  # "1.23E-10"
```

### Confidence interval (2 decimals)

```python
ci_low, ci_high = proportion_confint(n_sig, n_total, method='wilson')
answer = f"({round(ci_low, 2)}, {round(ci_high, 2)})"
```

## Format Detection

```python
def format_answer(value, question_text):
    """Auto-detect format from question text."""
    question_lower = question_text.lower()

    # Decimal places
    if "2 decimal" in question_lower:
        return round(value, 2)
    elif "4 decimal" in question_lower:
        return round(value, 4)
    elif "1 decimal" in question_lower:
        return round(value, 1)

    # Scientific notation
    if "scientific notation" in question_lower:
        return f"{value:.2E}"

    # Percentage
    if "percentage" in question_lower:
        if isinstance(value, float) and value < 1:
            return round(value * 100, 1)
        return round(value, 1)

    # Count
    if "how many" in question_lower:
        return int(value)

    # Default
    return value
```

## Examples by Question Type

### "How many genes show significant DE?"

```python
sig_genes = results[(results['padj'] < 0.05) & (results['log2FoldChange'].abs() > 0.5)]
answer = len(sig_genes)  # Integer: 842
```

### "What is the adjusted p-value for pathway X?"

```python
pathway = enr.results[enr.results['Term'].str.contains('ABC transporters')]
answer = round(pathway.iloc[0]['Adjusted P-value'], 4)  # 0.0234
```

### "What percentage of DEGs in A are also in B?"

```python
degs_A = set(results_A[results_A['padj'] < 0.05].index)
degs_B = set(results_B[results_B['padj'] < 0.05].index)
overlap = degs_A & degs_B
answer = round(len(overlap) / len(degs_A) * 100, 1)  # 15.3
```

### "What is the 95% CI for the proportion?"

```python
ci_low, ci_high = proportion_confint(n_sig, n_total, method='wilson')
answer = (round(ci_low, 2), round(ci_high, 2))  # (0.15, 0.25)
```

### "What is the log2FC of gene TP53?"

```python
answer = round(results.loc['TP53', 'log2FoldChange'], 2)  # 2.45
```

### "What is the median dispersion?"

```python
answer = f"{dds.var['dispersions'].median():.2E}"  # 1.23E-02
```

## Avoiding Common Mistakes

```python
# WRONG: Float when count expected
answer = 842.0  # Bad for "how many"

# RIGHT: Integer
answer = 842  # Good

# WRONG: Too many decimals
answer = 0.0234567  # Bad if question asks for 4 decimals

# RIGHT: Correct precision
answer = 0.0235  # Good

# WRONG: Scientific notation when not requested
answer = "8.42E+02"  # Bad for count

# RIGHT: Regular number
answer = 842  # Good

# WRONG: Missing percent sign
answer = 15.3  # Ambiguous

# RIGHT: Clear percentage
answer = "15.3%"  # OR answer = 15.3 if question says "as percentage"
```

## Validation Before Submission

```python
def validate_answer_format(answer, expected_type):
    """Validate answer format matches expected type."""
    if expected_type == 'integer':
        assert isinstance(answer, int), f"Expected int, got {type(answer)}"
    elif expected_type == 'float':
        assert isinstance(answer, (int, float)), f"Expected number, got {type(answer)}"
    elif expected_type == 'percentage':
        if isinstance(answer, str):
            assert '%' in answer, "Percentage should include % sign"
        else:
            assert 0 <= answer <= 100, "Percentage should be 0-100"
    elif expected_type == 'scientific':
        assert 'E' in str(answer) or 'e' in str(answer), "Should be in scientific notation"

    return True
```
