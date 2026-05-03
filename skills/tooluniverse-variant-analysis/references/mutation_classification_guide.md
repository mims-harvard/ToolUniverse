# Mutation Classification Guide

Complete reference for variant and mutation type classification in ToolUniverse variant analysis.

## Variant Type Classification

Variant types are determined from REF and ALT alleles.

| REF | ALT | Type | Description |
|-----|-----|------|-------------|
| A | G | SNV | Single nucleotide variant (substitution) |
| A | AT | INS | Insertion |
| AT | A | DEL | Deletion |
| AG | TC | MNV | Multi-nucleotide variant |
| AGC | TG | COMPLEX | Complex variant (combination of changes) |

## Mutation Type Classification

Mutation types are determined from consequence annotations in the VCF INFO field.

### Supported Annotation Formats

1. **SnpEff ANN field** (most common)
2. **VEP CSQ field**
3. **GATK Funcotator FUNCOTATION field**
4. **Standard INFO keys**: EFFECT, EFF, TYPE, CONSEQUENCE

### Consequence to Mutation Type Mapping

| Consequence Term | Mutation Type | Impact | Description |
|-----------------|---------------|--------|-------------|
| missense_variant | missense | MODERATE | Amino acid change |
| stop_gained | nonsense | HIGH | Premature stop codon |
| frameshift_variant | frameshift | HIGH | Reading frame shift |
| synonymous_variant | synonymous | LOW | No amino acid change |
| splice_acceptor_variant | splice_site | HIGH | Affects splice acceptor |
| splice_donor_variant | splice_site | HIGH | Affects splice donor |
| splice_region_variant | splice_region | LOW | Near splice site |
| inframe_insertion | inframe_insertion | MODERATE | In-frame amino acid insertion |
| inframe_deletion | inframe_deletion | MODERATE | In-frame amino acid deletion |
| intron_variant | intronic | MODIFIER | Within intron |
| intergenic_variant | intergenic | MODIFIER | Between genes |
| upstream_gene_variant | upstream | MODIFIER | Upstream of gene |
| downstream_gene_variant | downstream | MODIFIER | Downstream of gene |
| 5_prime_UTR_variant | UTR_5 | MODIFIER | In 5' UTR |
| 3_prime_UTR_variant | UTR_3 | MODIFIER | In 3' UTR |
| stop_lost | stop_lost | HIGH | Stop codon lost |
| start_lost | start_lost | HIGH | Start codon lost |
| non_coding_transcript_variant | non_coding | MODIFIER | In non-coding transcript |

### GATK Funcotator Terms

Also supported for backward compatibility:

| Funcotator Term | Maps to Mutation Type |
|----------------|----------------------|
| MISSENSE | missense |
| NONSENSE | nonsense |
| SILENT | synonymous |
| SPLICE_SITE | splice_site |
| FRAME_SHIFT_INS | frameshift |
| FRAME_SHIFT_DEL | frameshift |
| IN_FRAME_INS | inframe_insertion |
| IN_FRAME_DEL | inframe_deletion |
| INTRON | intronic |
| IGR | intergenic |
| FIVE_PRIME_UTR | UTR_5 |
| THREE_PRIME_UTR | UTR_3 |

## Impact Classification

Variants are classified by impact level:

| Impact | Mutation Types | Description |
|--------|---------------|-------------|
| **HIGH** | nonsense, frameshift, splice_site, stop_lost, start_lost | Likely loss of function |
| **MODERATE** | missense, inframe_insertion, inframe_deletion | Likely affects function |
| **LOW** | synonymous, splice_region | Unlikely to affect function |
| **MODIFIER** | intronic, intergenic, upstream, downstream, UTR_5, UTR_3 | Regulatory or non-coding |

## SnpEff ANN Field Format

SnpEff annotates variants with the ANN field in INFO:

```
ANN=T|missense_variant|MODERATE|BRCA1|BRCA1|transcript|NM_007294.3|protein_coding|11/22|c.5266dupC|p.Gln1756Profs|5382/7267|5266/5592|1756/1863||
```

**Parsed fields**:
1. Allele (T)
2. **Consequence** (missense_variant) → mapped to mutation type
3. **Impact** (MODERATE)
4. **Gene** (BRCA1)
5. Gene ID
6. Feature type (transcript)
7. **Transcript** (NM_007294.3)
8. Biotype
9. Rank
10. HGVS.c (c.5266dupC)
11. **HGVS.p** (p.Gln1756Profs) → protein change
12. cDNA position
13. CDS position
14. Protein position
15. Distance

## VEP CSQ Field Format

VEP annotates with CSQ field:

```
CSQ=T|missense_variant|MODERATE|BRCA1|ENSG00000012048|Transcript|ENST00000357654|protein_coding|11/22|c.5266dupC|p.Gln1756Profs|5382|5266|1756
```

**Parsed fields** (similar to SnpEff):
- Consequence → mutation type
- Impact
- Gene
- Transcript
- HGVS.c
- HGVS.p

## GATK Funcotator Format

GATK Funcotator uses FUNCOTATION field:

```
FUNCOTATION=[BRCA1|NM_007294.3|MISSENSE|c.5266dupC|p.Gln1756Profs|...]
```

## Examples

### Example 1: Missense Variant

**VCF line**:
```
chr17  43044295  .  C  T  100  PASS  ANN=T|missense_variant|MODERATE|BRCA1|BRCA1|transcript|NM_007294.3|protein_coding|11/22|c.1234G>A|p.Arg412His|1234/7267|1234/5592|412/1863||
```

**Classification**:
- Variant type: SNV (C → T)
- Mutation type: missense
- Impact: MODERATE
- Gene: BRCA1
- Protein change: p.Arg412His

### Example 2: Nonsense Variant

**VCF line**:
```
chr17  43045680  .  G  A  150  PASS  ANN=A|stop_gained|HIGH|TP53|TP53|transcript|NM_000546.5|protein_coding|7/11|c.817C>T|p.Arg273*|817/1200|817/1182|273/393||
```

**Classification**:
- Variant type: SNV (G → A)
- Mutation type: nonsense
- Impact: HIGH
- Gene: TP53
- Protein change: p.Arg273* (stop codon)

### Example 3: Frameshift Deletion

**VCF line**:
```
chr7  140753336  .  CA  C  120  PASS  ANN=C|frameshift_variant|HIGH|BRAF|BRAF|transcript|NM_004333.4|protein_coding|15/18|c.1799delA|p.Lys600fs|1799/2800|1799/2301|600/766||
```

**Classification**:
- Variant type: DEL (CA → C, deletion of A)
- Mutation type: frameshift
- Impact: HIGH
- Gene: BRAF

### Example 4: Intronic Variant

**VCF line**:
```
chr1  12345678  .  G  A  80  PASS  ANN=A|intron_variant|MODIFIER|GENE1|GENE1|transcript|NM_001234.1|protein_coding|5/10|c.456+10G>A||456||||
```

**Classification**:
- Variant type: SNV
- Mutation type: intronic
- Impact: MODIFIER
- Gene: GENE1

### Example 5: Splice Site Variant

**VCF line**:
```
chr2  23456789  .  C  T  200  PASS  ANN=T|splice_donor_variant|HIGH|GENE2|GENE2|transcript|NM_005678.2|protein_coding|8/12|c.789+1G>A||789||||
```

**Classification**:
- Variant type: SNV
- Mutation type: splice_site
- Impact: HIGH
- Gene: GENE2

## Mutation Type Hierarchy

When multiple consequences are present, the most severe is chosen:

1. **HIGH**: nonsense, frameshift, splice_site, stop_lost, start_lost
2. **MODERATE**: missense, inframe_insertion, inframe_deletion
3. **LOW**: synonymous, splice_region
4. **MODIFIER**: intronic, intergenic, upstream, downstream, UTR

## Unknown Mutations

If a variant has no annotation in the VCF:
- Mutation type: "unknown"
- Impact: "unknown"
- Gene: None

**Solution**: Either pre-annotate VCF with SnpEff/VEP, or enable ToolUniverse annotation.

## Filtering by Mutation Type

### Include Specific Mutation Types

```python
criteria = FilterCriteria(
    mutation_types=["missense", "nonsense", "frameshift"]
)
```

### Exclude Specific Consequences

```python
criteria = FilterCriteria(
    exclude_consequences=["intronic", "intergenic", "upstream", "downstream"]
)
```

### Include Only Coding Variants

```python
# Remove all MODIFIER impact variants
criteria = FilterCriteria(
    exclude_consequences=[
        "intronic",
        "intergenic",
        "upstream",
        "downstream",
        "UTR_5",
        "UTR_3"
    ]
)
```

## Statistics by Mutation Type

After parsing and classification:

```python
from python_implementation import compute_variant_statistics

stats = compute_variant_statistics(vcf_data.variants)

print(stats['mutation_types'])
# Output: {'missense': 412, 'nonsense': 23, 'frameshift': 15, 'synonymous': 298, ...}

print(stats['impacts'])
# Output: {'HIGH': 38, 'MODERATE': 427, 'LOW': 320, 'MODIFIER': 215}
```

## DataFrame Export

Convert to pandas for advanced mutation type analysis:

```python
from python_implementation import variants_to_dataframe

df = variants_to_dataframe(vcf_data.variants, sample="TUMOR")

# Group by mutation type
print(df.groupby('mutation_type').size())

# High-impact variants
high_impact = df[df['impact'] == 'HIGH']

# Missense variants in specific gene
brca1_missense = df[(df['gene'] == 'BRCA1') & (df['mutation_type'] == 'missense')]
```

## Annotation Fallback

If VCF lacks annotations:

```python
from python_implementation import variant_analysis_pipeline

# Enable ToolUniverse annotation
report = variant_analysis_pipeline(
    vcf_path="unannotated.vcf",
    annotate=True,
    max_annotate=100
)
```

This will:
1. Parse VCF (mutations will be "unknown")
2. Annotate top 100 variants with MyVariant.info
3. Update mutation types from MyVariant consequence data
4. Generate report with classified mutations

## Common Patterns

### High-Impact Variants Only
```python
criteria = FilterCriteria(
    mutation_types=["nonsense", "frameshift", "splice_site", "stop_lost", "start_lost"]
)
```

### Protein-Changing Variants
```python
criteria = FilterCriteria(
    mutation_types=["missense", "nonsense", "frameshift", "inframe_insertion", "inframe_deletion"]
)
```

### Loss-of-Function Variants
```python
criteria = FilterCriteria(
    mutation_types=["nonsense", "frameshift", "splice_site"]
)
```

### Coding Variants (Exclude MODIFIER)
```python
criteria = FilterCriteria(
    exclude_consequences=["intronic", "intergenic", "upstream", "downstream", "UTR_5", "UTR_3"]
)
```
