#!/usr/bin/env python3
"""
Variant Analysis and Annotation - Python SDK Implementation

Production-ready VCF processing, variant annotation, and mutation analysis
using local bioinformatics libraries + ToolUniverse databases.

Designed to solve BixBench-style variant analysis questions:
- VAF filtering and mutation type classification
- Variant annotation with consequence, impact, clinical significance
- Population frequency filtering (gnomAD, dbSNP)
- Multi-sample VCF comparison
- Intronic/intergenic filtering
"""

import os
import re
import sys
import gzip
import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class VariantRecord:
    """Represents a single variant from a VCF file."""
    chrom: str
    pos: int
    ref: str
    alt: str
    vid: str = ""             # variant ID (e.g., rsID)
    qual: float = 0.0
    filter_status: str = ""
    info: dict = field(default_factory=dict)
    format_fields: list = field(default_factory=list)
    sample_data: dict = field(default_factory=dict)
    # Derived fields
    variant_type: str = ""    # SNV, INS, DEL, MNV, COMPLEX
    vaf: dict = field(default_factory=dict)           # sample -> VAF
    genotype: dict = field(default_factory=dict)       # sample -> GT
    depth: dict = field(default_factory=dict)           # sample -> DP
    # Annotation fields
    consequence: str = ""
    impact: str = ""
    gene: str = ""
    transcript: str = ""
    protein_change: str = ""
    mutation_type: str = ""   # missense, nonsense, synonymous, etc.
    clinical_significance: str = ""
    population_freq: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.variant_type:
            self.variant_type = classify_variant_type(self.ref, self.alt)

    @property
    def key(self):
        return f"{self.chrom}:{self.pos}:{self.ref}>{self.alt}"


@dataclass
class VCFData:
    """Container for parsed VCF file data."""
    variants: list = field(default_factory=list)
    samples: list = field(default_factory=list)
    header_lines: list = field(default_factory=list)
    info_fields: dict = field(default_factory=dict)
    format_fields_meta: dict = field(default_factory=dict)
    contig_lines: list = field(default_factory=list)
    file_format: str = ""
    source: str = ""
    reference: str = ""
    total_lines: int = 0
    parse_errors: list = field(default_factory=list)


@dataclass
class FilterCriteria:
    """Configurable filter criteria for variants."""
    min_vaf: Optional[float] = None
    max_vaf: Optional[float] = None
    min_depth: Optional[int] = None
    min_qual: Optional[float] = None
    variant_types: Optional[list] = None        # SNV, INS, DEL, etc.
    mutation_types: Optional[list] = None        # missense, nonsense, etc.
    exclude_consequences: Optional[list] = None  # intronic, intergenic, etc.
    include_consequences: Optional[list] = None
    max_population_freq: Optional[float] = None
    min_population_freq: Optional[float] = None
    chromosomes: Optional[list] = None
    pass_only: bool = False
    sample: Optional[str] = None                # specific sample for multi-sample


@dataclass
class AnnotationResult:
    """Result of annotating a single variant."""
    variant_key: str = ""
    consequence: str = ""
    impact: str = ""
    gene_symbol: str = ""
    gene_id: str = ""
    transcript_id: str = ""
    protein_change: str = ""
    mutation_type: str = ""
    clinical_significance: str = ""
    cadd_phred: Optional[float] = None
    sift_score: Optional[float] = None
    sift_prediction: str = ""
    polyphen_score: Optional[float] = None
    polyphen_prediction: str = ""
    gnomad_af: Optional[float] = None
    gnomad_af_popmax: Optional[float] = None
    dbsnp_rsid: str = ""
    clinvar_classification: str = ""
    population_frequencies: dict = field(default_factory=dict)
    source: str = ""


@dataclass
class VariantAnalysisReport:
    """Comprehensive variant analysis report."""
    vcf_file: str = ""
    total_variants: int = 0
    total_samples: int = 0
    variants_by_type: dict = field(default_factory=dict)
    variants_by_consequence: dict = field(default_factory=dict)
    variants_by_mutation_type: dict = field(default_factory=dict)
    variants_by_chromosome: dict = field(default_factory=dict)
    variants_by_impact: dict = field(default_factory=dict)
    vaf_distribution: dict = field(default_factory=dict)
    clinical_variants: list = field(default_factory=list)
    filtered_count: int = 0
    annotation_count: int = 0
    warnings: list = field(default_factory=list)
    filters_applied: list = field(default_factory=list)
    timestamp: str = ""


# ---------------------------------------------------------------------------
# VCF Parsing (pure Python, streaming)
# ---------------------------------------------------------------------------

def classify_variant_type(ref: str, alt: str) -> str:
    """Classify variant type based on ref/alt alleles."""
    if alt in ('.', '*', '<*>'):
        return "NO_ALT"
    # Handle multi-allelic by taking first alt
    alt_allele = alt.split(',')[0]
    if len(ref) == 1 and len(alt_allele) == 1:
        return "SNV"
    elif len(ref) == 1 and len(alt_allele) > 1:
        return "INS"
    elif len(ref) > 1 and len(alt_allele) == 1:
        return "DEL"
    elif len(ref) == len(alt_allele) and len(ref) > 1:
        return "MNV"
    else:
        return "COMPLEX"


def parse_info_field(info_str: str) -> dict:
    """Parse VCF INFO field into dict."""
    if info_str == '.' or not info_str:
        return {}
    info = {}
    for item in info_str.split(';'):
        if '=' in item:
            key, val = item.split('=', 1)
            info[key] = val
        else:
            info[item] = True  # Flag fields
    return info


def parse_sample_field(format_str: str, sample_str: str) -> dict:
    """Parse VCF FORMAT and sample columns into dict."""
    if not format_str or not sample_str or format_str == '.' or sample_str == '.':
        return {}
    fields = format_str.split(':')
    values = sample_str.split(':')
    return dict(zip(fields, values))


def extract_vaf(sample_dict: dict) -> Optional[float]:
    """Extract VAF from sample data dict. Handles multiple VCF conventions."""
    # Direct AF/VAF field
    for key in ('AF', 'VAF', 'FREQ'):
        if key in sample_dict:
            try:
                val = sample_dict[key]
                if isinstance(val, str) and ',' in val:
                    val = val.split(',')[0]
                if isinstance(val, str) and val.endswith('%'):
                    return float(val.rstrip('%')) / 100.0
                return float(val)
            except (ValueError, TypeError):
                pass

    # Compute from AD (allelic depth): REF,ALT
    if 'AD' in sample_dict:
        try:
            ad_vals = sample_dict['AD'].split(',')
            if len(ad_vals) >= 2:
                ref_depth = int(ad_vals[0])
                alt_depth = int(ad_vals[1])
                total = ref_depth + alt_depth
                if total > 0:
                    return alt_depth / total
        except (ValueError, TypeError, IndexError):
            pass

    # Compute from AO/RO (FreeBayes style)
    if 'AO' in sample_dict and 'RO' in sample_dict:
        try:
            ao = int(sample_dict['AO'].split(',')[0])
            ro = int(sample_dict['RO'])
            total = ao + ro
            if total > 0:
                return ao / total
        except (ValueError, TypeError):
            pass

    # Compute from DP4 in info or NR/NV
    if 'NR' in sample_dict and 'NV' in sample_dict:
        try:
            nr = int(sample_dict['NR'])
            nv = int(sample_dict['NV'])
            if nr > 0:
                return nv / nr
        except (ValueError, TypeError):
            pass

    return None


def extract_depth(sample_dict: dict) -> Optional[int]:
    """Extract read depth from sample data."""
    if 'DP' in sample_dict:
        try:
            return int(sample_dict['DP'])
        except (ValueError, TypeError):
            pass
    if 'AD' in sample_dict:
        try:
            return sum(int(x) for x in sample_dict['AD'].split(','))
        except (ValueError, TypeError):
            pass
    return None


def extract_genotype(sample_dict: dict) -> str:
    """Extract genotype from sample data."""
    gt = sample_dict.get('GT', '.')
    return gt


def parse_vcf_line(line: str, samples: list) -> Optional[VariantRecord]:
    """Parse a single VCF data line into a VariantRecord."""
    parts = line.rstrip('\n\r').split('\t')
    if len(parts) < 8:
        return None

    chrom = parts[0].replace('chr', '')
    try:
        pos = int(parts[1])
    except ValueError:
        return None

    vid = parts[2] if parts[2] != '.' else ""
    ref = parts[3]
    alt = parts[4]

    try:
        qual = float(parts[5]) if parts[5] != '.' else 0.0
    except ValueError:
        qual = 0.0

    filter_status = parts[6]
    info = parse_info_field(parts[7])
    format_fields = parts[8].split(':') if len(parts) > 8 else []

    vaf_dict = {}
    gt_dict = {}
    dp_dict = {}
    sample_data_all = {}

    for i, sample_name in enumerate(samples):
        col_idx = 9 + i
        if col_idx < len(parts):
            sd = parse_sample_field(parts[8] if len(parts) > 8 else '', parts[col_idx])
            sample_data_all[sample_name] = sd
            v = extract_vaf(sd)
            if v is not None:
                vaf_dict[sample_name] = v
            d = extract_depth(sd)
            if d is not None:
                dp_dict[sample_name] = d
            gt_dict[sample_name] = extract_genotype(sd)

    # Also try extracting VAF from INFO field if per-sample VAF not found
    if not vaf_dict and 'AF' in info:
        try:
            af_val = float(info['AF'].split(',')[0])
            for s in samples:
                vaf_dict[s] = af_val
        except (ValueError, TypeError):
            pass

    record = VariantRecord(
        chrom=chrom,
        pos=pos,
        ref=ref,
        alt=alt,
        vid=vid,
        qual=qual,
        filter_status=filter_status,
        info=info,
        format_fields=format_fields,
        sample_data=sample_data_all,
        vaf=vaf_dict,
        genotype=gt_dict,
        depth=dp_dict,
    )
    return record


def parse_vcf(vcf_path: str, max_variants: int = 0) -> VCFData:
    """
    Parse a VCF file (supports .vcf, .vcf.gz).

    Args:
        vcf_path: Path to VCF file
        max_variants: Maximum variants to parse (0 = unlimited)

    Returns:
        VCFData with parsed variants and metadata
    """
    vcf_data = VCFData(source=vcf_path)

    if not os.path.exists(vcf_path):
        vcf_data.parse_errors.append(f"File not found: {vcf_path}")
        return vcf_data

    opener = gzip.open if vcf_path.endswith('.gz') else open
    mode = 'rt' if vcf_path.endswith('.gz') else 'r'

    samples = []
    variants = []
    line_count = 0

    try:
        with opener(vcf_path, mode) as f:
            for line in f:
                line_count += 1
                line = line.rstrip('\n\r')

                if line.startswith('##'):
                    vcf_data.header_lines.append(line)
                    if line.startswith('##fileformat='):
                        vcf_data.file_format = line.split('=', 1)[1]
                    elif line.startswith('##INFO='):
                        _parse_meta_field(line, vcf_data.info_fields)
                    elif line.startswith('##FORMAT='):
                        _parse_meta_field(line, vcf_data.format_fields_meta)
                    elif line.startswith('##contig='):
                        vcf_data.contig_lines.append(line)
                    elif line.startswith('##reference='):
                        vcf_data.reference = line.split('=', 1)[1]
                    continue

                if line.startswith('#CHROM'):
                    parts = line.split('\t')
                    if len(parts) > 9:
                        samples = parts[9:]
                    vcf_data.samples = samples
                    continue

                # Data line
                try:
                    record = parse_vcf_line(line, samples)
                    if record is not None:
                        # Extract annotation from INFO if present (e.g., ANN, CSQ, FUNCOTATION)
                        _extract_info_annotations(record)
                        variants.append(record)
                except Exception as e:
                    vcf_data.parse_errors.append(f"Line {line_count}: {str(e)[:100]}")

                if max_variants > 0 and len(variants) >= max_variants:
                    break

    except Exception as e:
        vcf_data.parse_errors.append(f"File read error: {str(e)}")

    vcf_data.variants = variants
    vcf_data.total_lines = line_count
    return vcf_data


def _parse_meta_field(line: str, target_dict: dict):
    """Parse ##INFO or ##FORMAT meta lines."""
    match = re.match(r'##\w+=<(.+)>', line)
    if match:
        content = match.group(1)
        id_match = re.search(r'ID=([^,]+)', content)
        desc_match = re.search(r'Description="([^"]*)"', content)
        type_match = re.search(r'Type=([^,]+)', content)
        number_match = re.search(r'Number=([^,]+)', content)
        if id_match:
            target_dict[id_match.group(1)] = {
                'description': desc_match.group(1) if desc_match else '',
                'type': type_match.group(1) if type_match else '',
                'number': number_match.group(1) if number_match else '',
            }


def _extract_info_annotations(record: VariantRecord):
    """Extract variant annotations from INFO field (SnpEff ANN, VEP CSQ, etc.)."""
    info = record.info

    # SnpEff ANN field
    if 'ANN' in info and isinstance(info['ANN'], str):
        ann_entries = info['ANN'].split(',')
        if ann_entries:
            first_ann = ann_entries[0].split('|')
            if len(first_ann) >= 11:
                record.consequence = first_ann[1] if len(first_ann) > 1 else ""
                record.impact = first_ann[2] if len(first_ann) > 2 else ""
                record.gene = first_ann[3] if len(first_ann) > 3 else ""
                record.transcript = first_ann[6] if len(first_ann) > 6 else ""
                record.protein_change = first_ann[10] if len(first_ann) > 10 else ""
                record.mutation_type = _consequence_to_mutation_type(record.consequence)

    # VEP CSQ field
    elif 'CSQ' in info and isinstance(info['CSQ'], str):
        csq_entries = info['CSQ'].split(',')
        if csq_entries:
            first_csq = csq_entries[0].split('|')
            if len(first_csq) >= 7:
                record.consequence = first_csq[1] if len(first_csq) > 1 else ""
                record.impact = first_csq[2] if len(first_csq) > 2 else ""
                record.gene = first_csq[3] if len(first_csq) > 3 else ""
                record.transcript = first_csq[6] if len(first_csq) > 6 else ""
                record.mutation_type = _consequence_to_mutation_type(record.consequence)

    # FUNCOTATION (GATK Funcotator)
    elif 'FUNCOTATION' in info and isinstance(info['FUNCOTATION'], str):
        func = info['FUNCOTATION'].strip('[]')
        func_fields = func.split('|')
        if len(func_fields) >= 6:
            record.gene = func_fields[0] if func_fields[0] else ""
            record.consequence = func_fields[5] if len(func_fields) > 5 else ""
            record.mutation_type = _consequence_to_mutation_type(record.consequence)

    # SnpSift/VCF-standard fields
    if not record.consequence:
        for key in ('EFFECT', 'EFF', 'TYPE', 'Consequence'):
            if key in info and isinstance(info[key], str):
                record.consequence = info[key].split(',')[0].split('(')[0]
                record.mutation_type = _consequence_to_mutation_type(record.consequence)
                break

    # Gene from INFO
    if not record.gene:
        for key in ('GENE', 'Gene', 'SYMBOL', 'Gene.refGene'):
            if key in info and isinstance(info[key], str):
                record.gene = info[key]
                break

    # Clinical significance
    if 'CLNSIG' in info:
        record.clinical_significance = str(info['CLNSIG']).replace('_', ' ')
    elif 'ClinicalSignificance' in info:
        record.clinical_significance = str(info['ClinicalSignificance'])


# ---------------------------------------------------------------------------
# Mutation type classification
# ---------------------------------------------------------------------------

# Standard SO consequence terms to mutation type mapping
CONSEQUENCE_TO_MUTATION_TYPE = {
    # High impact
    'transcript_ablation': 'transcript_ablation',
    'splice_acceptor_variant': 'splice_site',
    'splice_donor_variant': 'splice_site',
    'stop_gained': 'nonsense',
    'frameshift_variant': 'frameshift',
    'stop_lost': 'stop_lost',
    'start_lost': 'start_lost',
    'transcript_amplification': 'amplification',
    # Moderate impact
    'inframe_insertion': 'inframe_insertion',
    'inframe_deletion': 'inframe_deletion',
    'missense_variant': 'missense',
    'protein_altering_variant': 'protein_altering',
    # Low impact
    'splice_region_variant': 'splice_region',
    'incomplete_terminal_codon_variant': 'incomplete_terminal_codon',
    'start_retained_variant': 'synonymous',
    'stop_retained_variant': 'synonymous',
    'synonymous_variant': 'synonymous',
    # Modifier (non-coding)
    'coding_sequence_variant': 'coding_sequence',
    'mature_miRNA_variant': 'miRNA',
    '5_prime_UTR_variant': 'UTR_5',
    '3_prime_UTR_variant': 'UTR_3',
    'non_coding_transcript_exon_variant': 'non_coding_exon',
    'intron_variant': 'intronic',
    'NMD_transcript_variant': 'NMD',
    'non_coding_transcript_variant': 'non_coding',
    'upstream_gene_variant': 'upstream',
    'downstream_gene_variant': 'downstream',
    'intergenic_variant': 'intergenic',
    'regulatory_region_variant': 'regulatory',
    'regulatory_region_ablation': 'regulatory',
    'TF_binding_site_variant': 'TF_binding',
    # SnpEff-style
    'missense_variant&splice_region_variant': 'missense',
    'synonymous_variant&splice_region_variant': 'synonymous',
    'frameshift_variant&stop_gained': 'frameshift',
    'frameshift_variant&splice_region_variant': 'frameshift',
    'stop_gained&splice_region_variant': 'nonsense',
    # GATK Funcotator style
    'MISSENSE': 'missense',
    'NONSENSE': 'nonsense',
    'SILENT': 'synonymous',
    'SPLICE_SITE': 'splice_site',
    'FRAME_SHIFT_INS': 'frameshift',
    'FRAME_SHIFT_DEL': 'frameshift',
    'IN_FRAME_INS': 'inframe_insertion',
    'IN_FRAME_DEL': 'inframe_deletion',
    'NONSTOP': 'stop_lost',
    'START_CODON_SNP': 'start_lost',
    'DE_NOVO_START_IN_FRAME': 'start_gained',
    'DE_NOVO_START_OUT_FRAME': 'start_gained',
    'FIVE_PRIME_UTR': 'UTR_5',
    'THREE_PRIME_UTR': 'UTR_3',
    'INTRON': 'intronic',
    'FIVE_PRIME_FLANK': 'upstream',
    'THREE_PRIME_FLANK': 'downstream',
    'IGR': 'intergenic',
    'LINCRNA': 'non_coding',
    'RNA': 'non_coding',
    'COULD_NOT_DETERMINE': 'unknown',
}

# Consequence terms that are intronic or intergenic
INTRONIC_INTERGENIC_TERMS = {
    'intronic', 'intergenic', 'upstream', 'downstream',
    'intron_variant', 'intergenic_variant', 'upstream_gene_variant',
    'downstream_gene_variant', 'INTRON', 'IGR',
    'non_coding', 'non_coding_exon', 'regulatory', 'TF_binding',
}


def _consequence_to_mutation_type(consequence: str) -> str:
    """Map VCF consequence annotation to standardized mutation type."""
    if not consequence:
        return "unknown"
    # Handle combined consequences (e.g., "missense_variant&splice_region_variant")
    # Try exact match first
    if consequence in CONSEQUENCE_TO_MUTATION_TYPE:
        return CONSEQUENCE_TO_MUTATION_TYPE[consequence]
    # Try first term of combined
    first_term = consequence.split('&')[0].strip()
    if first_term in CONSEQUENCE_TO_MUTATION_TYPE:
        return CONSEQUENCE_TO_MUTATION_TYPE[first_term]
    # Case-insensitive search
    for key, val in CONSEQUENCE_TO_MUTATION_TYPE.items():
        if key.lower() == consequence.lower():
            return val
    return consequence.lower().replace(' ', '_')


def classify_mutation_type_from_ref_alt(ref: str, alt: str) -> str:
    """Classify mutation type purely from ref/alt (without annotation)."""
    vtype = classify_variant_type(ref, alt)
    if vtype == "SNV":
        return "SNV"
    elif vtype == "INS":
        return "insertion"
    elif vtype == "DEL":
        return "deletion"
    elif vtype == "MNV":
        return "MNV"
    return "complex"


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def filter_variants(variants: list, criteria: FilterCriteria) -> tuple:
    """
    Filter variants based on criteria. Returns (passing, failing).

    Args:
        variants: List of VariantRecord
        criteria: FilterCriteria object

    Returns:
        Tuple of (passing_variants, failing_variants)
    """
    passing = []
    failing = []

    for v in variants:
        passes = True

        # VAF filter
        if criteria.min_vaf is not None or criteria.max_vaf is not None:
            sample = criteria.sample
            if sample and sample in v.vaf:
                vaf_val = v.vaf[sample]
            elif v.vaf:
                vaf_val = list(v.vaf.values())[0]
            else:
                vaf_val = None

            if vaf_val is not None:
                if criteria.min_vaf is not None and vaf_val < criteria.min_vaf:
                    passes = False
                if criteria.max_vaf is not None and vaf_val > criteria.max_vaf:
                    # Use strict > so that max_vaf=0.3 includes variants at exactly 0.3
                    passes = False

        # Depth filter
        if criteria.min_depth is not None:
            sample = criteria.sample
            if sample and sample in v.depth:
                dp = v.depth[sample]
            elif v.depth:
                dp = list(v.depth.values())[0]
            else:
                dp = None
            if dp is not None and dp < criteria.min_depth:
                passes = False

        # Quality filter
        if criteria.min_qual is not None and v.qual < criteria.min_qual:
            passes = False

        # PASS filter
        if criteria.pass_only and v.filter_status not in ('PASS', '.', ''):
            passes = False

        # Variant type filter
        if criteria.variant_types and v.variant_type not in criteria.variant_types:
            passes = False

        # Mutation type filter
        if criteria.mutation_types:
            mt = v.mutation_type.lower() if v.mutation_type else ""
            if not any(ct.lower() in mt or mt in ct.lower() for ct in criteria.mutation_types):
                passes = False

        # Consequence exclusion
        if criteria.exclude_consequences and v.mutation_type:
            mt = v.mutation_type.lower()
            consequence_raw = v.consequence.lower() if v.consequence else ""
            if any(exc.lower() in mt or exc.lower() in consequence_raw
                   for exc in criteria.exclude_consequences):
                passes = False

        # Consequence inclusion
        if criteria.include_consequences and v.mutation_type:
            mt = v.mutation_type.lower()
            consequence_raw = v.consequence.lower() if v.consequence else ""
            if not any(inc.lower() in mt or inc.lower() in consequence_raw
                       for inc in criteria.include_consequences):
                passes = False

        # Population frequency filter
        if criteria.max_population_freq is not None and v.population_freq:
            max_pf = max(v.population_freq.values()) if v.population_freq else 0
            if max_pf > criteria.max_population_freq:
                passes = False

        if criteria.min_population_freq is not None and v.population_freq:
            max_pf = max(v.population_freq.values()) if v.population_freq else 0
            if max_pf < criteria.min_population_freq:
                passes = False

        # Chromosome filter
        if criteria.chromosomes:
            norm_chrom = v.chrom.replace('chr', '')
            if norm_chrom not in [c.replace('chr', '') for c in criteria.chromosomes]:
                passes = False

        if passes:
            passing.append(v)
        else:
            failing.append(v)

    return passing, failing


def filter_non_reference_variants(variants: list) -> list:
    """Remove variants where all samples are homozygous reference (0/0 or ./.)."""
    result = []
    for v in variants:
        if not v.genotype:
            # No genotype info; keep variant
            result.append(v)
            continue
        has_alt = False
        for gt in v.genotype.values():
            gt_clean = gt.replace('|', '/').replace('.', '0')
            alleles = gt_clean.split('/')
            if any(a != '0' for a in alleles):
                has_alt = True
                break
        if has_alt:
            result.append(v)
    return result


def filter_intronic_intergenic(variants: list) -> tuple:
    """
    Filter out intronic and intergenic variants.

    Returns:
        (non_intronic_intergenic, intronic_intergenic)
    """
    # Mutation types that are purely intronic/intergenic (no coding impact)
    PURE_INTRONIC_INTERGENIC_TYPES = {
        'intronic', 'intergenic', 'upstream', 'downstream',
    }
    PURE_INTRONIC_INTERGENIC_CONSEQUENCES = {
        'intron_variant', 'intergenic_variant',
        'upstream_gene_variant', 'downstream_gene_variant',
    }

    passing = []
    excluded = []
    for v in variants:
        mt = v.mutation_type.lower() if v.mutation_type else ""
        consequence = v.consequence.lower() if v.consequence else ""

        # Only exclude purely intronic/intergenic variants
        # Do NOT exclude splice_region (which may co-occur with intron_variant)
        is_intronic_ig = (
            mt in PURE_INTRONIC_INTERGENIC_TYPES or
            consequence in PURE_INTRONIC_INTERGENIC_CONSEQUENCES
        )
        if is_intronic_ig:
            excluded.append(v)
        else:
            passing.append(v)
    return passing, excluded


# ---------------------------------------------------------------------------
# Statistics and analysis
# ---------------------------------------------------------------------------

def compute_variant_statistics(variants: list, samples: list = None) -> dict:
    """Compute comprehensive statistics for a list of variants."""
    stats = {
        'total_variants': len(variants),
        'variant_types': Counter(),
        'mutation_types': Counter(),
        'consequences': Counter(),
        'impacts': Counter(),
        'chromosomes': Counter(),
        'genes': Counter(),
        'clinical_significance': Counter(),
        'filter_status': Counter(),
        'vaf_stats': {},
        'depth_stats': {},
        'samples': samples or [],
        'ti_tv_ratio': None,
    }

    transitions = 0
    transversions = 0
    all_vafs = defaultdict(list)
    all_depths = defaultdict(list)

    for v in variants:
        stats['variant_types'][v.variant_type] += 1
        if v.mutation_type:
            stats['mutation_types'][v.mutation_type] += 1
        if v.consequence:
            stats['consequences'][v.consequence.split('&')[0]] += 1
        if v.impact:
            stats['impacts'][v.impact] += 1
        stats['chromosomes'][v.chrom] += 1
        if v.gene:
            stats['genes'][v.gene] += 1
        if v.clinical_significance:
            stats['clinical_significance'][v.clinical_significance] += 1
        stats['filter_status'][v.filter_status or 'MISSING'] += 1

        # Ti/Tv
        if v.variant_type == "SNV":
            ref_alt = (v.ref.upper(), v.alt.split(',')[0].upper())
            if ref_alt in (('A', 'G'), ('G', 'A'), ('C', 'T'), ('T', 'C')):
                transitions += 1
            else:
                transversions += 1

        # VAF per sample
        for sample, vaf_val in v.vaf.items():
            all_vafs[sample].append(vaf_val)

        # Depth per sample
        for sample, dp_val in v.depth.items():
            all_depths[sample].append(dp_val)

    if transversions > 0:
        stats['ti_tv_ratio'] = round(transitions / transversions, 3)

    # VAF summary per sample
    for sample, vafs in all_vafs.items():
        if vafs:
            stats['vaf_stats'][sample] = {
                'mean': round(sum(vafs) / len(vafs), 4),
                'median': round(sorted(vafs)[len(vafs) // 2], 4),
                'min': round(min(vafs), 4),
                'max': round(max(vafs), 4),
                'count': len(vafs),
            }

    # Depth summary per sample
    for sample, depths in all_depths.items():
        if depths:
            stats['depth_stats'][sample] = {
                'mean': round(sum(depths) / len(depths), 1),
                'median': sorted(depths)[len(depths) // 2],
                'min': min(depths),
                'max': max(depths),
            }

    return stats


def compute_vaf_mutation_crosstab(variants: list, sample: str = None) -> dict:
    """
    Compute cross-tabulation of VAF ranges vs mutation types.

    Returns dict with keys like 'vaf_bins', 'mutation_types', 'crosstab'
    """
    vaf_bins = [(0, 0.1), (0.1, 0.2), (0.2, 0.3), (0.3, 0.4), (0.4, 0.5), (0.5, 1.0)]
    bin_labels = ['0-0.1', '0.1-0.2', '0.2-0.3', '0.3-0.4', '0.4-0.5', '0.5-1.0']

    crosstab = defaultdict(lambda: defaultdict(int))
    total_by_bin = defaultdict(int)
    total_by_type = defaultdict(int)

    for v in variants:
        # Get VAF
        if sample and sample in v.vaf:
            vaf_val = v.vaf[sample]
        elif v.vaf:
            vaf_val = list(v.vaf.values())[0]
        else:
            continue

        mt = v.mutation_type if v.mutation_type else "unknown"

        for (lo, hi), label in zip(vaf_bins, bin_labels):
            if lo <= vaf_val < hi or (hi == 1.0 and vaf_val == 1.0):
                crosstab[label][mt] += 1
                total_by_bin[label] += 1
                total_by_type[mt] += 1
                break

    return {
        'vaf_bins': bin_labels,
        'mutation_types': dict(total_by_type),
        'crosstab': {k: dict(v) for k, v in crosstab.items()},
        'totals_by_bin': dict(total_by_bin),
    }


def fraction_of_vaf_filtered_by_mutation_type(
    variants: list,
    max_vaf: float,
    mutation_type: str,
    sample: str = None,
) -> dict:
    """
    Answer: "What fraction of variants with VAF < X are annotated as Y mutations?"

    Args:
        variants: List of VariantRecord
        max_vaf: VAF threshold (exclusive upper bound)
        mutation_type: Mutation type to check (e.g., 'missense')
        sample: Sample name for multi-sample VCFs

    Returns:
        Dict with numerator, denominator, fraction
    """
    below_vaf = []
    for v in variants:
        if sample and sample in v.vaf:
            vaf_val = v.vaf[sample]
        elif v.vaf:
            vaf_val = list(v.vaf.values())[0]
        else:
            continue
        if vaf_val < max_vaf:
            below_vaf.append(v)

    mt_lower = mutation_type.lower()
    matching = [v for v in below_vaf
                if mt_lower in (v.mutation_type or '').lower()
                or mt_lower in (v.consequence or '').lower()]

    denom = len(below_vaf)
    numer = len(matching)

    return {
        'total_below_vaf': denom,
        'matching_mutation_type': numer,
        'fraction': round(numer / denom, 6) if denom > 0 else 0.0,
        'vaf_threshold': max_vaf,
        'mutation_type': mutation_type,
    }


def compare_cohort_mutation_frequency(
    vcf_data_list: list,
    mutation_type: str,
    cohort_names: list = None,
) -> dict:
    """
    Compare mutation type frequency between cohorts (different VCF files or sample groups).

    Args:
        vcf_data_list: List of VCFData objects (one per cohort)
        mutation_type: Mutation type to compare
        cohort_names: Names for each cohort

    Returns:
        Dict with per-cohort frequencies and difference
    """
    if cohort_names is None:
        cohort_names = [f"Cohort_{i+1}" for i in range(len(vcf_data_list))]

    results = {}
    for name, vcf_data in zip(cohort_names, vcf_data_list):
        total = len(vcf_data.variants)
        mt_lower = mutation_type.lower()
        matching = sum(1 for v in vcf_data.variants
                       if mt_lower in (v.mutation_type or '').lower()
                       or mt_lower in (v.consequence or '').lower())
        freq = matching / total if total > 0 else 0
        results[name] = {
            'total_variants': total,
            'matching_variants': matching,
            'frequency': round(freq, 6),
        }

    freqs = [r['frequency'] for r in results.values()]
    if len(freqs) >= 2:
        diff = round(abs(freqs[0] - freqs[1]), 6)
    else:
        diff = None

    return {
        'cohorts': results,
        'mutation_type': mutation_type,
        'frequency_difference': diff,
    }


def count_non_reference_after_filtering(
    variants: list,
    exclude_intronic_intergenic: bool = True,
) -> dict:
    """
    Count non-reference variants remaining after filtering intronic/intergenic.

    Args:
        variants: List of VariantRecord
        exclude_intronic_intergenic: Whether to exclude intronic/intergenic

    Returns:
        Dict with counts
    """
    # First filter non-reference
    non_ref = filter_non_reference_variants(variants)

    if exclude_intronic_intergenic:
        passing, excluded = filter_intronic_intergenic(non_ref)
    else:
        passing = non_ref
        excluded = []

    return {
        'total_input': len(variants),
        'non_reference': len(non_ref),
        'excluded_intronic_intergenic': len(excluded),
        'remaining': len(passing),
    }


# ---------------------------------------------------------------------------
# ToolUniverse annotation integration
# ---------------------------------------------------------------------------

def annotate_variant_with_myvariant(tu, variant: VariantRecord) -> AnnotationResult:
    """
    Annotate a variant using MyVariant.info (aggregates ClinVar, dbSNP, gnomAD, CADD, etc.).

    Args:
        tu: ToolUniverse instance (loaded)
        variant: VariantRecord to annotate

    Returns:
        AnnotationResult with all available annotations
    """
    result = AnnotationResult(variant_key=variant.key)

    # Build query: try rsID first, then HGVS
    query = None
    if variant.vid and variant.vid.startswith('rs'):
        query = variant.vid
    else:
        # Build HGVS-style query
        query = f"chr{variant.chrom}:g.{variant.pos}{variant.ref}>{variant.alt}"

    try:
        mv_result = tu.tools.MyVariant_query_variants(query=query)
        hits = mv_result.get('hits', [])
        if not hits:
            return result

        hit = hits[0]

        # ClinVar
        clinvar = hit.get('clinvar', {})
        if isinstance(clinvar, dict):
            gene_info = clinvar.get('gene', {})
            if isinstance(gene_info, dict):
                result.gene_symbol = gene_info.get('symbol', '')
                result.gene_id = str(gene_info.get('id', ''))
            hgvs = clinvar.get('hgvs', {})
            if isinstance(hgvs, dict):
                protein_list = hgvs.get('protein', [])
                if isinstance(protein_list, list) and protein_list:
                    result.protein_change = protein_list[0]
                elif isinstance(protein_list, str):
                    result.protein_change = protein_list

            # Clinical significance from RCV
            rcv = clinvar.get('rcv', [])
            if isinstance(rcv, list) and rcv:
                sig = rcv[0].get('clinical_significance', '') if isinstance(rcv[0], dict) else ''
                result.clinvar_classification = sig
            elif isinstance(rcv, dict):
                result.clinvar_classification = rcv.get('clinical_significance', '')

        # dbSNP
        dbsnp = hit.get('dbsnp', {})
        if isinstance(dbsnp, dict):
            result.dbsnp_rsid = dbsnp.get('rsid', '')
            if not result.gene_symbol:
                genes = dbsnp.get('gene', [])
                if isinstance(genes, list) and genes:
                    g = genes[0]
                    if isinstance(g, dict):
                        result.gene_symbol = g.get('symbol', '') or g.get('name', '')
                    elif isinstance(g, str):
                        result.gene_symbol = g
                elif isinstance(genes, dict):
                    result.gene_symbol = genes.get('symbol', '') or genes.get('name', '')

        # CADD
        cadd = hit.get('cadd', {})
        if isinstance(cadd, dict):
            result.cadd_phred = cadd.get('phred')
            result.consequence = cadd.get('consequence', '')
            # SIFT from CADD
            sift = cadd.get('sift', {})
            if isinstance(sift, dict):
                result.sift_score = sift.get('val')
                result.sift_prediction = sift.get('cat', '')
            # PolyPhen from CADD
            polyphen = cadd.get('polyphen', {})
            if isinstance(polyphen, dict):
                result.polyphen_score = polyphen.get('val')
                result.polyphen_prediction = polyphen.get('cat', '')

        # gnomAD
        gnomad = hit.get('gnomad_genome', {})
        if isinstance(gnomad, dict):
            af = gnomad.get('af', {})
            if isinstance(af, dict):
                result.gnomad_af = af.get('af')
                # Find popmax
                pop_keys = [k for k in af.keys() if k.startswith('af_') and '_' not in k[3:]]
                if pop_keys:
                    result.gnomad_af_popmax = max(af.get(k, 0) or 0 for k in pop_keys)
                result.population_frequencies = {k: v for k, v in af.items()
                                                  if isinstance(v, (int, float))}
            elif isinstance(af, (int, float)):
                result.gnomad_af = af

        # Determine mutation type from consequence
        if result.consequence:
            result.mutation_type = _consequence_to_mutation_type(result.consequence)

        # Impact classification
        if result.mutation_type in ('nonsense', 'frameshift', 'splice_site', 'stop_lost', 'start_lost'):
            result.impact = 'HIGH'
        elif result.mutation_type in ('missense', 'inframe_insertion', 'inframe_deletion', 'protein_altering'):
            result.impact = 'MODERATE'
        elif result.mutation_type in ('synonymous', 'splice_region'):
            result.impact = 'LOW'
        elif result.mutation_type in ('intronic', 'intergenic', 'upstream', 'downstream',
                                       'UTR_5', 'UTR_3', 'non_coding'):
            result.impact = 'MODIFIER'

        result.source = 'MyVariant.info'

    except Exception as e:
        logger.warning(f"MyVariant annotation failed for {variant.key}: {e}")

    return result


def annotate_variant_with_dbsnp(tu, variant: VariantRecord) -> dict:
    """Annotate variant using dbSNP tool."""
    if not variant.vid or not variant.vid.startswith('rs'):
        return {}
    try:
        result = tu.tools.dbsnp_get_variant_by_rsid(rsid=variant.vid)
        if isinstance(result, dict) and result.get('status') == 'success':
            return result.get('data', {})
    except Exception as e:
        logger.warning(f"dbSNP annotation failed for {variant.vid}: {e}")
    return {}


def annotate_variant_with_gnomad(tu, variant: VariantRecord) -> dict:
    """Annotate variant using gnomAD tool."""
    variant_id = f"{variant.chrom}-{variant.pos}-{variant.ref}-{variant.alt.split(',')[0]}"
    try:
        result = tu.tools.gnomad_get_variant(variant_id=variant_id)
        if isinstance(result, dict):
            data = result.get('data', {})
            if isinstance(data, dict):
                return data.get('data', {}).get('variant', {})
    except Exception as e:
        logger.warning(f"gnomAD annotation failed for {variant_id}: {e}")
    return {}


def annotate_variant_with_ensembl_vep(tu, variant: VariantRecord) -> dict:
    """Annotate variant using Ensembl VEP."""
    if variant.vid and variant.vid.startswith('rs'):
        try:
            result = tu.tools.EnsemblVEP_annotate_rsid(variant_id=variant.vid)
            if isinstance(result, dict):
                if 'data' in result and isinstance(result['data'], list):
                    return result['data'][0] if result['data'] else {}
                elif 'error' not in result:
                    return result
        except Exception as e:
            logger.warning(f"VEP rsID annotation failed for {variant.vid}: {e}")

    # Try region-based VEP
    try:
        region = f"{variant.chrom}:{variant.pos}:{variant.pos}/{variant.alt.split(',')[0]}"
        result = tu.tools.ensembl_vep_region(region=region, species='homo_sapiens')
        if isinstance(result, dict):
            if 'data' in result:
                data = result['data']
                if isinstance(data, list) and data:
                    return data[0]
                elif isinstance(data, dict):
                    return data
    except Exception as e:
        logger.warning(f"VEP region annotation failed for {variant.key}: {e}")

    return {}


def batch_annotate_variants(
    tu,
    variants: list,
    use_myvariant: bool = True,
    use_dbsnp: bool = False,
    use_gnomad: bool = False,
    use_vep: bool = False,
    max_annotate: int = 100,
) -> list:
    """
    Batch annotate variants using ToolUniverse databases.

    Args:
        tu: ToolUniverse instance (loaded)
        variants: List of VariantRecord
        use_myvariant: Use MyVariant.info (recommended, aggregates many sources)
        use_dbsnp: Use dbSNP directly
        use_gnomad: Use gnomAD directly
        use_vep: Use Ensembl VEP
        max_annotate: Maximum variants to annotate (API rate limiting)

    Returns:
        List of AnnotationResult
    """
    annotations = []
    to_annotate = variants[:max_annotate]

    for i, v in enumerate(to_annotate):
        if (i + 1) % 10 == 0:
            logger.info(f"Annotating variant {i+1}/{len(to_annotate)}")

        ann = AnnotationResult(variant_key=v.key)

        if use_myvariant:
            mv_ann = annotate_variant_with_myvariant(tu, v)
            if mv_ann.gene_symbol:
                ann = mv_ann

        if use_dbsnp and v.vid and v.vid.startswith('rs'):
            dbsnp_data = annotate_variant_with_dbsnp(tu, v)
            if dbsnp_data:
                if not ann.dbsnp_rsid:
                    ann.dbsnp_rsid = dbsnp_data.get('rsid', '')
                if not ann.gene_symbol and dbsnp_data.get('genes'):
                    ann.gene_symbol = dbsnp_data['genes'][0]
                if not ann.clinvar_classification and dbsnp_data.get('clinical_significance'):
                    ann.clinvar_classification = ', '.join(dbsnp_data['clinical_significance'])
                if not ann.population_frequencies and dbsnp_data.get('allele_frequencies'):
                    for af_entry in dbsnp_data['allele_frequencies']:
                        study = af_entry.get('study', '')
                        freq_str = af_entry.get('freq', '')
                        if '=' in freq_str:
                            try:
                                freq_val = float(freq_str.split('=')[1].split('/')[0])
                                ann.population_frequencies[study] = freq_val
                            except (ValueError, IndexError):
                                pass

        if use_gnomad:
            gnomad_data = annotate_variant_with_gnomad(tu, v)
            if gnomad_data and not ann.gnomad_af:
                ann.gnomad_af = gnomad_data.get('genome', {}).get('af')

        # Update the original variant record with annotations
        if ann.gene_symbol and not v.gene:
            v.gene = ann.gene_symbol
        if ann.mutation_type and not v.mutation_type:
            v.mutation_type = ann.mutation_type
        if ann.consequence and not v.consequence:
            v.consequence = ann.consequence
        if ann.impact and not v.impact:
            v.impact = ann.impact
        if ann.clinical_significance and not v.clinical_significance:
            v.clinical_significance = ann.clinical_significance
        if ann.protein_change and not v.protein_change:
            v.protein_change = ann.protein_change

        annotations.append(ann)

    return annotations


# ---------------------------------------------------------------------------
# DataFrame conversion
# ---------------------------------------------------------------------------

def variants_to_dataframe(variants: list, sample: str = None) -> pd.DataFrame:
    """
    Convert variants to a pandas DataFrame for analysis.

    Args:
        variants: List of VariantRecord
        sample: Specific sample for VAF/depth (uses first sample if None)

    Returns:
        DataFrame with variant data
    """
    rows = []
    for v in variants:
        # Get sample-specific data
        if sample and sample in v.vaf:
            vaf_val = v.vaf[sample]
        elif v.vaf:
            vaf_val = list(v.vaf.values())[0]
        else:
            vaf_val = None

        if sample and sample in v.depth:
            dp_val = v.depth[sample]
        elif v.depth:
            dp_val = list(v.depth.values())[0]
        else:
            dp_val = None

        if sample and sample in v.genotype:
            gt_val = v.genotype[sample]
        elif v.genotype:
            gt_val = list(v.genotype.values())[0]
        else:
            gt_val = None

        rows.append({
            'chrom': v.chrom,
            'pos': v.pos,
            'ref': v.ref,
            'alt': v.alt,
            'id': v.vid,
            'qual': v.qual,
            'filter': v.filter_status,
            'variant_type': v.variant_type,
            'vaf': vaf_val,
            'depth': dp_val,
            'genotype': gt_val,
            'gene': v.gene,
            'consequence': v.consequence,
            'impact': v.impact,
            'mutation_type': v.mutation_type,
            'protein_change': v.protein_change,
            'clinical_significance': v.clinical_significance,
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# cyvcf2-based parsing (faster for large files)
# ---------------------------------------------------------------------------

def parse_vcf_cyvcf2(vcf_path: str, max_variants: int = 0) -> VCFData:
    """
    Parse VCF using cyvcf2 (faster C-based parser). Falls back to pure Python.

    Args:
        vcf_path: Path to VCF file
        max_variants: Maximum variants to parse (0 = unlimited)

    Returns:
        VCFData
    """
    try:
        from cyvcf2 import VCF
    except ImportError:
        logger.warning("cyvcf2 not installed, falling back to pure Python parser")
        return parse_vcf(vcf_path, max_variants)

    vcf_data = VCFData(source=vcf_path)

    if not os.path.exists(vcf_path):
        vcf_data.parse_errors.append(f"File not found: {vcf_path}")
        return vcf_data

    try:
        vcf_reader = VCF(vcf_path)
        vcf_data.samples = list(vcf_reader.samples)
        variants = []

        for variant in vcf_reader:
            chrom = str(variant.CHROM).replace('chr', '')
            pos = variant.POS
            ref = variant.REF
            alts = variant.ALT
            alt = ','.join(alts) if alts else '.'

            vid = variant.ID if variant.ID else ""
            qual = variant.QUAL if variant.QUAL is not None else 0.0
            filt = variant.FILTER if variant.FILTER else 'PASS'

            # Build info dict from available fields
            info_dict = {}
            try:
                for key in variant.INFO:
                    try:
                        info_dict[key] = str(variant.INFO.get(key, ''))
                    except Exception:
                        pass
            except Exception:
                pass

            # Sample data
            vaf_dict = {}
            gt_dict = {}
            dp_dict = {}
            sample_data_all = {}

            for i, sample_name in enumerate(vcf_data.samples):
                sd = {}
                # Genotype
                try:
                    gt = variant.genotypes[i]
                    gt_str = '/'.join(str(a) for a in gt[:-1])
                    if gt[-1]:  # phased
                        gt_str = '|'.join(str(a) for a in gt[:-1])
                    gt_dict[sample_name] = gt_str
                    sd['GT'] = gt_str
                except Exception:
                    pass

                # Depth
                try:
                    dp = variant.format('DP')
                    if dp is not None:
                        dp_val = int(dp[i][0])
                        dp_dict[sample_name] = dp_val
                        sd['DP'] = str(dp_val)
                except Exception:
                    pass

                # AD (allelic depth)
                try:
                    ad = variant.format('AD')
                    if ad is not None:
                        ad_vals = ad[i]
                        sd['AD'] = ','.join(str(int(x)) for x in ad_vals)
                        if len(ad_vals) >= 2:
                            total = sum(int(x) for x in ad_vals)
                            if total > 0:
                                vaf_dict[sample_name] = int(ad_vals[1]) / total
                except Exception:
                    pass

                # AF field
                if sample_name not in vaf_dict:
                    try:
                        af = variant.format('AF')
                        if af is not None:
                            vaf_dict[sample_name] = float(af[i][0])
                            sd['AF'] = str(af[i][0])
                    except Exception:
                        pass

                sample_data_all[sample_name] = sd

            record = VariantRecord(
                chrom=chrom,
                pos=pos,
                ref=ref,
                alt=alt,
                vid=vid,
                qual=qual,
                filter_status=filt if isinstance(filt, str) else str(filt),
                info=info_dict,
                sample_data=sample_data_all,
                vaf=vaf_dict,
                genotype=gt_dict,
                depth=dp_dict,
            )

            _extract_info_annotations(record)
            variants.append(record)

            if max_variants > 0 and len(variants) >= max_variants:
                break

        vcf_data.variants = variants
        vcf_reader.close()

    except Exception as e:
        vcf_data.parse_errors.append(f"cyvcf2 error: {str(e)}")
        logger.warning(f"cyvcf2 failed, falling back to pure Python: {e}")
        return parse_vcf(vcf_path, max_variants)

    return vcf_data


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_variant_report(
    vcf_data: VCFData,
    annotations: list = None,
    filters_applied: list = None,
    output_file: str = None,
) -> str:
    """
    Generate a comprehensive markdown variant analysis report.

    Args:
        vcf_data: Parsed VCF data
        annotations: Optional annotation results
        filters_applied: List of filter descriptions
        output_file: Output file path

    Returns:
        Path to generated report
    """
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"variant_analysis_report_{timestamp}.md"

    stats = compute_variant_statistics(vcf_data.variants, vcf_data.samples)
    report = []

    report.append("# Variant Analysis Report\n\n")
    report.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append(f"**VCF Source**: {vcf_data.source}\n")
    report.append(f"**File Format**: {vcf_data.file_format or 'VCF'}\n")
    report.append(f"**Samples**: {len(vcf_data.samples)} ({', '.join(vcf_data.samples[:10])}{'...' if len(vcf_data.samples) > 10 else ''})\n\n")

    if filters_applied:
        report.append("**Filters Applied**:\n")
        for f in filters_applied:
            report.append(f"- {f}\n")
        report.append("\n")

    report.append("---\n\n")

    # Summary
    report.append("## 1. Summary Statistics\n\n")
    report.append(f"| Metric | Value |\n")
    report.append(f"|--------|-------|\n")
    report.append(f"| Total Variants | {stats['total_variants']:,} |\n")
    report.append(f"| SNVs | {stats['variant_types'].get('SNV', 0):,} |\n")
    report.append(f"| Insertions | {stats['variant_types'].get('INS', 0):,} |\n")
    report.append(f"| Deletions | {stats['variant_types'].get('DEL', 0):,} |\n")
    report.append(f"| MNVs | {stats['variant_types'].get('MNV', 0):,} |\n")
    if stats['ti_tv_ratio'] is not None:
        report.append(f"| Ti/Tv Ratio | {stats['ti_tv_ratio']} |\n")
    report.append("\n")

    # Mutation types
    if stats['mutation_types']:
        report.append("## 2. Mutation Type Distribution\n\n")
        report.append("| Mutation Type | Count | Percentage |\n")
        report.append("|--------------|-------|------------|\n")
        total = stats['total_variants']
        for mt, count in stats['mutation_types'].most_common(20):
            pct = round(100 * count / total, 2) if total > 0 else 0
            report.append(f"| {mt} | {count:,} | {pct}% |\n")
        report.append("\n")

    # Impact distribution
    if stats['impacts']:
        report.append("## 3. Impact Distribution\n\n")
        report.append("| Impact | Count | Percentage |\n")
        report.append("|--------|-------|------------|\n")
        for impact, count in stats['impacts'].most_common():
            pct = round(100 * count / stats['total_variants'], 2) if stats['total_variants'] > 0 else 0
            report.append(f"| {impact} | {count:,} | {pct}% |\n")
        report.append("\n")

    # Chromosome distribution
    report.append("## 4. Chromosome Distribution\n\n")
    report.append("| Chromosome | Count |\n")
    report.append("|-----------|-------|\n")
    for chrom in sorted(stats['chromosomes'].keys(), key=lambda x: (len(x), x)):
        report.append(f"| {chrom} | {stats['chromosomes'][chrom]:,} |\n")
    report.append("\n")

    # VAF statistics
    if stats['vaf_stats']:
        report.append("## 5. VAF Distribution\n\n")
        for sample, vaf_s in stats['vaf_stats'].items():
            report.append(f"### Sample: {sample}\n\n")
            report.append(f"| Metric | Value |\n")
            report.append(f"|--------|-------|\n")
            report.append(f"| Mean VAF | {vaf_s['mean']} |\n")
            report.append(f"| Median VAF | {vaf_s['median']} |\n")
            report.append(f"| Min VAF | {vaf_s['min']} |\n")
            report.append(f"| Max VAF | {vaf_s['max']} |\n")
            report.append(f"| Variants with VAF | {vaf_s['count']} |\n")
            report.append("\n")

    # Clinical significance
    if stats['clinical_significance']:
        report.append("## 6. Clinical Significance\n\n")
        report.append("| Classification | Count |\n")
        report.append("|---------------|-------|\n")
        for cls, count in stats['clinical_significance'].most_common():
            report.append(f"| {cls} | {count:,} |\n")
        report.append("\n")

    # Top genes
    if stats['genes']:
        report.append("## 7. Top Mutated Genes\n\n")
        report.append("| Gene | Variant Count |\n")
        report.append("|------|---------------|\n")
        for gene, count in stats['genes'].most_common(30):
            if gene:
                report.append(f"| {gene} | {count:,} |\n")
        report.append("\n")

    # Annotations
    if annotations:
        report.append("## 8. Variant Annotations\n\n")
        clinical_anns = [a for a in annotations if a.clinvar_classification]
        if clinical_anns:
            report.append(f"### ClinVar Annotated Variants ({len(clinical_anns)})\n\n")
            report.append("| Variant | Gene | ClinVar | CADD | gnomAD AF |\n")
            report.append("|---------|------|---------|------|----------|\n")
            for a in clinical_anns[:50]:
                cadd = f"{a.cadd_phred:.1f}" if a.cadd_phred else "N/A"
                af = f"{a.gnomad_af:.6f}" if a.gnomad_af else "N/A"
                report.append(f"| {a.variant_key} | {a.gene_symbol} | {a.clinvar_classification} | {cadd} | {af} |\n")
            report.append("\n")

    # Parse errors
    if vcf_data.parse_errors:
        report.append("## Warnings and Errors\n\n")
        for err in vcf_data.parse_errors[:20]:
            report.append(f"- {err}\n")
        report.append("\n")

    report.append("---\n\n")
    report.append("*Generated by tooluniverse-variant-analysis*\n")

    with open(output_file, 'w') as f:
        f.write(''.join(report))

    return output_file


# ---------------------------------------------------------------------------
# High-level pipeline functions
# ---------------------------------------------------------------------------

def variant_analysis_pipeline(
    vcf_path: str,
    output_file: str = None,
    filters: FilterCriteria = None,
    annotate: bool = False,
    max_annotate: int = 100,
    use_cyvcf2: bool = True,
    max_variants: int = 0,
) -> VariantAnalysisReport:
    """
    Complete variant analysis pipeline.

    Args:
        vcf_path: Path to VCF file
        output_file: Output report path
        filters: Optional filter criteria
        annotate: Whether to annotate with ToolUniverse databases
        max_annotate: Max variants to annotate
        use_cyvcf2: Use cyvcf2 for faster parsing
        max_variants: Max variants to parse (0 = all)

    Returns:
        VariantAnalysisReport
    """
    report = VariantAnalysisReport(
        vcf_file=vcf_path,
        timestamp=datetime.now().isoformat(),
    )

    # Parse
    if use_cyvcf2:
        vcf_data = parse_vcf_cyvcf2(vcf_path, max_variants)
    else:
        vcf_data = parse_vcf(vcf_path, max_variants)

    report.total_variants = len(vcf_data.variants)
    report.total_samples = len(vcf_data.samples)
    report.warnings.extend(vcf_data.parse_errors)

    # Filter
    if filters:
        passing, failing = filter_variants(vcf_data.variants, filters)
        report.filtered_count = len(failing)
        vcf_data.variants = passing
        report.filters_applied.append(str(filters))

    # Statistics
    stats = compute_variant_statistics(vcf_data.variants, vcf_data.samples)
    report.variants_by_type = dict(stats['variant_types'])
    report.variants_by_mutation_type = dict(stats['mutation_types'])
    report.variants_by_chromosome = dict(stats['chromosomes'])
    report.variants_by_impact = dict(stats['impacts'])
    report.vaf_distribution = stats['vaf_stats']

    # Annotate
    annotations = []
    if annotate:
        try:
            from tooluniverse import ToolUniverse
            tu = ToolUniverse()
            tu.load_tools()
            annotations = batch_annotate_variants(
                tu, vcf_data.variants,
                use_myvariant=True,
                max_annotate=max_annotate,
            )
            report.annotation_count = len(annotations)
            report.clinical_variants = [
                {'key': a.variant_key, 'gene': a.gene_symbol,
                 'clinvar': a.clinvar_classification, 'cadd': a.cadd_phred}
                for a in annotations if a.clinvar_classification
            ]
        except Exception as e:
            report.warnings.append(f"Annotation failed: {str(e)}")

    # Generate report file
    filters_desc = []
    if filters:
        if filters.min_vaf is not None:
            filters_desc.append(f"Min VAF: {filters.min_vaf}")
        if filters.max_vaf is not None:
            filters_desc.append(f"Max VAF: {filters.max_vaf}")
        if filters.min_depth is not None:
            filters_desc.append(f"Min Depth: {filters.min_depth}")
        if filters.pass_only:
            filters_desc.append("PASS only")
        if filters.exclude_consequences:
            filters_desc.append(f"Excluded: {', '.join(filters.exclude_consequences)}")

    if output_file:
        generate_variant_report(
            vcf_data, annotations, filters_desc, output_file
        )

    return report


# ---------------------------------------------------------------------------
# Convenience functions for BixBench-style questions
# ---------------------------------------------------------------------------

def answer_vaf_mutation_fraction(
    vcf_path: str,
    max_vaf: float = 0.3,
    mutation_type: str = "missense",
    sample: str = None,
    use_cyvcf2: bool = True,
) -> dict:
    """
    Answer: "What fraction of variants with VAF < X are annotated as Y mutations?"

    Args:
        vcf_path: Path to VCF file
        max_vaf: VAF threshold
        mutation_type: Mutation type to check
        sample: Sample name for multi-sample VCFs
        use_cyvcf2: Use cyvcf2 parser

    Returns:
        Dict with fraction and counts
    """
    if use_cyvcf2:
        vcf_data = parse_vcf_cyvcf2(vcf_path)
    else:
        vcf_data = parse_vcf(vcf_path)

    return fraction_of_vaf_filtered_by_mutation_type(
        vcf_data.variants, max_vaf, mutation_type, sample
    )


def answer_cohort_comparison(
    vcf_paths: list,
    mutation_type: str = "missense",
    cohort_names: list = None,
    use_cyvcf2: bool = True,
) -> dict:
    """
    Answer: "What is the difference in mutation frequency between cohorts?"

    Args:
        vcf_paths: List of VCF file paths (one per cohort)
        mutation_type: Mutation type to compare
        cohort_names: Names for each cohort
        use_cyvcf2: Use cyvcf2 parser

    Returns:
        Dict with per-cohort frequencies and difference
    """
    parser = parse_vcf_cyvcf2 if use_cyvcf2 else parse_vcf
    vcf_data_list = [parser(p) for p in vcf_paths]
    return compare_cohort_mutation_frequency(vcf_data_list, mutation_type, cohort_names)


def answer_non_reference_after_filter(
    vcf_path: str,
    exclude_intronic_intergenic: bool = True,
    use_cyvcf2: bool = True,
) -> dict:
    """
    Answer: "After filtering intronic/intergenic variants, how many non-reference variants remain?"

    Args:
        vcf_path: Path to VCF file
        exclude_intronic_intergenic: Whether to exclude intronic/intergenic
        use_cyvcf2: Use cyvcf2 parser

    Returns:
        Dict with counts
    """
    if use_cyvcf2:
        vcf_data = parse_vcf_cyvcf2(vcf_path)
    else:
        vcf_data = parse_vcf(vcf_path)

    return count_non_reference_after_filtering(
        vcf_data.variants, exclude_intronic_intergenic
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Variant Analysis Pipeline")
    parser.add_argument("vcf", help="Input VCF file path")
    parser.add_argument("-o", "--output", help="Output report path")
    parser.add_argument("--annotate", action="store_true", help="Annotate with ToolUniverse")
    parser.add_argument("--max-annotate", type=int, default=100, help="Max variants to annotate")
    parser.add_argument("--min-vaf", type=float, help="Minimum VAF filter")
    parser.add_argument("--max-vaf", type=float, help="Maximum VAF filter")
    parser.add_argument("--min-depth", type=int, help="Minimum depth filter")
    parser.add_argument("--pass-only", action="store_true", help="Only PASS variants")
    parser.add_argument("--max-variants", type=int, default=0, help="Max variants to parse")

    args = parser.parse_args()

    filters = FilterCriteria(
        min_vaf=args.min_vaf,
        max_vaf=args.max_vaf,
        min_depth=args.min_depth,
        pass_only=args.pass_only,
    )

    report = variant_analysis_pipeline(
        vcf_path=args.vcf,
        output_file=args.output,
        filters=filters,
        annotate=args.annotate,
        max_annotate=args.max_annotate,
        max_variants=args.max_variants,
    )

    print(f"Total variants: {report.total_variants}")
    print(f"Variants by type: {report.variants_by_type}")
    print(f"Variants by mutation type: {report.variants_by_mutation_type}")
    if report.warnings:
        print(f"Warnings: {report.warnings}")
