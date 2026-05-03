# Tool Description Quick Reference Checklist

Use this checklist when reviewing or creating tool descriptions.

## Per-Tool Review Checklist

Copy and check off for each tool:

```
Tool: ___________________________

CRITICAL FIXES:
[ ] Required inputs clearly marked ("**Required: Provide ONE input type**")
[ ] Mutually exclusive options numbered (**Option 1**, **Option 2**)
[ ] Prerequisites stated if first tool in family
[ ] Critical abbreviations expanded on first use

HIGH PRIORITY:
[ ] Filter parameters list available fields
[ ] Filter parameters show operators (==, !=, in, etc.)
[ ] Filter parameters include 2-3 examples
[ ] Parameters with choices explain trade-offs
[ ] Default values recommended with reasoning

MEDIUM PRIORITY:
[ ] File size warnings where relevant ("Files can be large (GBs)")
[ ] Web form vs API results clarified
[ ] File types explained ("cooler (multi-resolution matrices)")
[ ] "Use for:" section with 3-5 concrete use cases

VALIDATION:
[ ] JSON syntax validated (python3 -m json.tool)
[ ] Description 30-60 words (not too short, not too long)
[ ] No time-sensitive information
[ ] Consistent terminology throughout
```

## Common Abbreviations to Expand

First use only - expand as "Abbreviation (Full Name)":

**Bioinformatics:**
- [ ] H5AD → HDF5-based AnnData
- [ ] RPM → Reads Per Million
- [ ] TPM → Transcripts Per Million
- [ ] FPKM → Fragments Per Kilobase Million
- [ ] TSS → Transcription Start Site
- [ ] TAD → Topologically Associating Domain
- [ ] QTL → Quantitative Trait Locus
- [ ] GWAS → Genome-Wide Association Study

**Technical:**
- [ ] API → Application Programming Interface
- [ ] REST → Representational State Transfer
- [ ] DRS → Data Repository Service
- [ ] URI → Uniform Resource Identifier
- [ ] UUID → Universally Unique Identifier

**Methods:**
- [ ] MACS2 → Model-based Analysis of ChIP-Seq
- [ ] IUPAC → International Union of Pure and Applied Chemistry (nucleotide codes)
- [ ] QC → Quality Control

## Parameter Description Templates

### Filter Parameters
```
"Filter using SQL-like syntax. Format: 'field == \"value\"'. 
Operators: ==, !=, in, <, >, <=, >=. Combine with 'and'/'or'. 
Common fields: [list 5-10 fields]. 
Examples: [3 diverse examples]."
```

### Threshold/Stringency Parameters
```
"[Purpose]. Options: 'X'=[value] ([outcome], [when to use]), 
'Y'=[value] ([outcome], [when to use]), 'Z'=[value] ([outcome], [when to use]). 
Default 'X' suitable for most analyses. [Trade-off principle]."
```

### Version/Selection Parameters
```
"[Purpose]. 'option1' (recommended, [characteristic]), 
'option2' ([characteristic], [caveat]), or [format] ([use case]). 
Default 'option1' is best for [scenario]."
```

### Input Data Parameters
```
"**Option N**: [Format description]. [When to use]. 
Example: [concrete example with actual values]."
```

## Description Structure Formula

```
[Action verb] to [purpose]. [Prerequisites if first tool]. 
[Key data/scale]. [Required inputs if mutually exclusive]. 
[Note about limitations]. Use for: [use case 1], [use case 2], 
[use case 3].
```

## Quick Fixes Reference

| Problem | Solution | Pattern |
|---------|----------|---------|
| Unclear if ONE or ALL inputs needed | Add "**Required: Provide ONE input type**" | Bold + explicit |
| Users don't know options | Number as (1), (2), (3) in description | Numbered list |
| Parameters unclear | Label as "**Option 1**", "**Option 2**" | Bold labels |
| Missing prerequisites | Add "Prerequisites: Requires 'package'" | Front-load |
| Abbreviation unclear | Expand as "ABC (Full Name)" | Parenthetical |
| Filter syntax unknown | List operators and fields | Explicit list |
| Parameter choice unclear | Explain trade-offs and recommend | Comparative |
| File size unknown | Add "Note: Files can be large (GBs)" | Size warning |

## Validation Commands

```bash
# Validate single file
python3 -m json.tool src/tooluniverse/data/your_tools.json > /dev/null && echo "✓ Valid"

# Validate all tools
for f in src/tooluniverse/data/*_tools.json; do
  python3 -m json.tool "$f" > /dev/null && echo "✓ $(basename $f) valid"
done

# Count tools per file
grep -c '"name":' src/tooluniverse/data/*_tools.json

# Check for common issues
grep -n "TODO\|FIXME\|XXX" src/tooluniverse/data/*_tools.json
```

## Quality Thresholds

### Minimum Acceptable
- [ ] Purpose stated
- [ ] Parameters described
- [ ] JSON valid

### Good
- [ ] Prerequisites mentioned
- [ ] Examples provided
- [ ] Use cases listed
- [ ] Abbreviations expanded

### Excellent
- [ ] All critical items checked
- [ ] Filter fields listed
- [ ] Parameter trade-offs explained
- [ ] Mutually exclusive options numbered
- [ ] File size warnings where needed
- [ ] 30-second test passes
- [ ] First-try test passes

## Before/After Metrics

Track improvements:

```
Before:
- Description length: ___ words
- Abbreviations unexpanded: ___
- Parameters without guidance: ___
- Missing prerequisites: Yes/No
- Mutually exclusive clarity: Yes/No

After:
- Description length: ___ words
- Abbreviations expanded: ___
- Parameters with guidance: ___
- Prerequisites stated: Yes/No
- Mutually exclusive clarity: Yes/No

Expected impact:
- Error rate reduction: ~___% 
- Time to first success: ~___% faster
```
