# Antibody Engineering - Workflow Details

Detailed code examples and implementation guidance for each workflow phase. See `SKILL.md` for the high-level workflow overview.

---

## Phase 1: Input Analysis & Characterization

### 1.1 Sequence Annotation

```python
def annotate_antibody_sequence(sequence):
    """Annotate antibody sequence with CDRs and framework regions."""

    # Use IMGT numbering scheme (standard for antibodies)
    # CDR definitions (IMGT):
    # CDR-H1: 27-38, CDR-H2: 56-65, CDR-H3: 105-117
    # CDR-L1: 27-38, CDR-L2: 56-65, CDR-L3: 105-117

    annotation = {
        'sequence': sequence,
        'length': len(sequence),
        'regions': {
            'FR1': sequence[0:26],
            'CDR1': sequence[26:38],
            'FR2': sequence[38:55],
            'CDR2': sequence[55:65],
            'FR3': sequence[65:104],
            'CDR3': sequence[104:117],
            'FR4': sequence[117:]
        }
    }

    return annotation
```

### 1.2 Species & Germline Identification

```python
def identify_germline(tu, vh_sequence, vl_sequence):
    """Identify germline genes for VH and VL chains using IMGT."""

    vh_germlines = tu.tools.IMGT_search_genes(
        gene_type="IGHV",
        species="Homo sapiens"
    )

    vl_germlines = tu.tools.IMGT_search_genes(
        gene_type="IGKV",  # or IGLV for lambda
        species="Homo sapiens"
    )

    # Get sequences for top matches
    # Calculate identity % for each germline
    # Return closest matches

    return {
        'vh_germline': 'IGHV1-69*01',
        'vh_identity': 87.2,
        'vl_germline': 'IGKV1-39*01',
        'vl_identity': 89.5
    }
```

### 1.3 Clinical Precedent Search

```python
def search_clinical_precedents(tu, target_antigen):
    """Find approved/clinical antibodies against same target."""

    therapeutics = tu.tools.TheraSAbDab_search_by_target(
        target=target_antigen
    )

    approved = [ab for ab in therapeutics if ab['phase'] == 'Approved']
    clinical = [ab for ab in therapeutics if 'Phase' in ab['phase']]

    return {
        'approved_count': len(approved),
        'clinical_count': len(clinical),
        'examples': approved[:3],
        'insights': extract_design_patterns(approved)
    }
```

---

## Phase 2: Humanization Strategy

### 2.1 Framework Selection

```python
def select_human_framework(tu, mouse_sequence, cdr_sequences):
    """Select optimal human framework for CDR grafting."""

    vh_genes = tu.tools.IMGT_search_genes(
        gene_type="IGHV",
        species="Homo sapiens"
    )

    candidates = []
    for gene in vh_genes[:20]:  # Top 20 human germlines
        gene_seq = tu.tools.IMGT_get_sequence(
            accession=gene['accession'],
            format='fasta'
        )

        score = calculate_framework_score(
            mouse_fr=extract_framework(mouse_sequence),
            human_fr=extract_framework(gene_seq),
            cdr_compatibility=check_cdr_compatibility(cdr_sequences, gene_seq)
        )

        candidates.append({
            'germline': gene['name'],
            'identity': score['identity'],
            'cdr_compatibility': score['cdr_compatibility'],
            'clinical_use': count_clinical_uses(gene['name']),
            'overall_score': score['total']
        })

    return sorted(candidates, key=lambda x: x['overall_score'], reverse=True)
```

### 2.2 CDR Grafting Design

```python
def design_cdr_grafting(mouse_sequence, human_framework, cdr_sequences):
    """Design CDR grafting with backmutation identification."""

    grafted_sequence = graft_cdrs(
        human_framework=human_framework,
        mouse_cdrs=cdr_sequences
    )

    # Vernier zone residues (affect CDR conformation)
    vernier_residues = [2, 27, 28, 29, 30, 47, 48, 67, 69, 71, 78, 93, 94]

    backmutations = []
    for pos in vernier_residues:
        if mouse_sequence[pos] != human_framework[pos]:
            backmutations.append({
                'position': pos,
                'human_aa': human_framework[pos],
                'mouse_aa': mouse_sequence[pos],
                'reason': 'Vernier zone - may affect CDR conformation',
                'priority': 'High' if pos in [27, 29, 30, 48] else 'Medium'
            })

    return {
        'grafted_sequence': grafted_sequence,
        'backmutations': backmutations,
        'humanness_score': calculate_humanness(grafted_sequence)
    }
```

### 2.3 Humanization Scoring

```python
def calculate_humanization_score(sequence, human_germline):
    """Calculate comprehensive humanization score."""

    fr_identity = calculate_framework_identity(sequence, human_germline)
    tcell_epitope_count = predict_tcell_epitopes(sequence)
    unusual_residues = count_unusual_residues(sequence)
    aggregation_motifs = find_aggregation_motifs(sequence)

    score = {
        'framework_humanness': fr_identity,       # 0-100%
        'cdr_preservation': 100,                   # Always 100% initially
        'tcell_epitopes': tcell_epitope_count,
        'unusual_residues': unusual_residues,
        'aggregation_risk': len(aggregation_motifs),
        'overall_score': calculate_weighted_score(
            fr_identity, tcell_epitope_count, unusual_residues, aggregation_motifs
        )
    }

    return score
```

---

## Phase 3: Structure Modeling & Analysis

### 3.1 AlphaFold Structure Prediction

```python
def predict_antibody_structure(tu, vh_sequence, vl_sequence):
    """Predict antibody Fv structure using AlphaFold."""

    fv_sequence = vh_sequence + ":" + vl_sequence

    prediction = tu.tools.alphafold_get_prediction(
        sequence=fv_sequence,
        return_format='pdb'
    )

    plddt_scores = extract_plddt(prediction)

    regions = {
        'VH_FR': np.mean([plddt_scores[i] for i in range(0, 26)]),
        'CDR_H1': np.mean([plddt_scores[i] for i in range(26, 38)]),
        'CDR_H2': np.mean([plddt_scores[i] for i in range(55, 65)]),
        'CDR_H3': np.mean([plddt_scores[i] for i in range(104, 117)]),
    }

    return {
        'structure': prediction,
        'mean_plddt': np.mean(plddt_scores),
        'regional_plddt': regions,
        'cdr_confidence': np.mean([regions['CDR_H1'], regions['CDR_H2'], regions['CDR_H3']])
    }
```

### 3.2 CDR Conformation Analysis

```python
def analyze_cdr_conformation(structure):
    """Analyze CDR loop conformations and canonical classes."""

    cdr_coords = extract_cdr_regions(structure)

    cdr_classes = {
        'CDR-H1': classify_canonical_structure(cdr_coords['H1']),
        'CDR-H2': classify_canonical_structure(cdr_coords['H2']),
        'CDR-H3': 'Non-canonical (14 aa)',
        'CDR-L1': classify_canonical_structure(cdr_coords['L1']),
        'CDR-L2': classify_canonical_structure(cdr_coords['L2']),
        'CDR-L3': classify_canonical_structure(cdr_coords['L3'])
    }

    rmsd_values = calculate_canonical_rmsd(cdr_coords, cdr_classes)

    return {
        'classes': cdr_classes,
        'rmsd': rmsd_values,
        'confidence': assess_conformation_confidence(rmsd_values)
    }
```

### 3.3 Epitope Mapping

```python
def map_epitope(tu, target_protein, antibody_structure):
    """Identify epitope on target protein."""

    target_info = tu.tools.UniProt_get_entry_by_accession(
        accession=target_protein
    )

    epitopes = tu.tools.iedb_search_epitopes(
        sequence_contains=target_protein,
        structure_type="Linear peptide",
        limit=20
    )

    sabdab_results = tu.tools.SAbDab_search_structures(
        query=target_info['protein_name']
    )

    return {
        'epitope_candidates': epitopes,
        'structural_precedents': sabdab_results,
        'predicted_interface': predict_binding_interface(antibody_structure)
    }
```

---

## Phase 4: Affinity Optimization

### 4.1 In Silico Mutation Screening

```python
def design_affinity_variants(antibody_structure, target_structure):
    """Design affinity maturation variants using computational screening."""

    interface_residues = identify_interface_residues(
        antibody_structure,
        target_structure,
        distance_cutoff=4.5
    )

    cdr_interface = [res for res in interface_residues if is_cdr_residue(res)]

    variants = []
    for position in cdr_interface:
        for aa in 'ACDEFGHIKLMNPQRSTVWY':
            if aa != antibody_structure.sequence[position]:
                predicted_ddg = predict_binding_energy_change(
                    structure=antibody_structure,
                    mutation=f"{antibody_structure.sequence[position]}{position}{aa}"
                )

                if predicted_ddg < -0.5:
                    variants.append({
                        'position': position,
                        'original': antibody_structure.sequence[position],
                        'mutant': aa,
                        'predicted_ddg': predicted_ddg,
                        'predicted_kd_fold': calculate_kd_change(predicted_ddg)
                    })

    return sorted(variants, key=lambda x: x['predicted_ddg'])
```

### 4.2 CDR Optimization Strategies

```python
def cdr_optimization_strategies(cdr_sequence, cdr_name):
    """Identify CDR optimization strategies based on sequence and structure."""

    strategies = []

    # Strategy 1: CDR-H3 extension
    if len(cdr_sequence) < 12 and cdr_name == 'CDR-H3':
        strategies.append({
            'strategy': 'CDR-H3 extension',
            'rationale': 'Add 1-2 residues to increase contact surface',
            'expected_impact': '+2-5x affinity improvement'
        })

    # Strategy 2: Tyrosine enrichment
    if cdr_sequence.count('Y') < 2:
        strategies.append({
            'strategy': 'Tyrosine enrichment',
            'rationale': 'Tyr provides pi-stacking and H-bonds',
            'expected_impact': '+2-3x affinity improvement'
        })

    # Strategy 3: Salt bridge formation
    if 'PD' in cdr_sequence or 'EP' in cdr_sequence:
        strategies.append({
            'strategy': 'Salt bridge formation',
            'rationale': 'Charged residues for electrostatic interactions',
            'expected_impact': '+1-2x affinity and pH sensitivity'
        })

    return strategies
```

---

## Phase 5: Developability Assessment

### 5.1 Aggregation Propensity

```python
def assess_aggregation(sequence):
    """Comprehensive aggregation risk assessment."""

    aprs = find_aggregation_motifs(sequence)
    hydrophobic_patches = identify_surface_hydrophobic(sequence)
    charge_patches = identify_charge_clusters(sequence)
    tango_score = predict_tango_score(sequence)
    aggrescan_score = predict_aggrescan(sequence)
    pi = calculate_isoelectric_point(sequence)

    return {
        'apr_count': len(aprs),
        'apr_regions': aprs,
        'hydrophobic_patches': hydrophobic_patches,
        'tango_score': tango_score,
        'aggrescan_score': aggrescan_score,
        'pi': pi,
        'overall_risk': categorize_risk(tango_score, aggrescan_score, len(aprs))
    }
```

### 5.2 PTM Site Identification

```python
def identify_ptm_sites(sequence):
    """Identify post-translational modification liability sites."""

    ptm_sites = {
        'deamidation': [],    # NG, NS motifs
        'isomerization': [],  # DG, DS motifs
        'oxidation': [],      # Met, Trp residues
        'glycosylation': []   # N-X-S/T motif (X != P)
    }

    for i, aa in enumerate(sequence[:-1]):
        if aa == 'N' and sequence[i+1] in ['G', 'S']:
            ptm_sites['deamidation'].append({
                'position': i,
                'motif': sequence[i:i+2],
                'risk': 'High' if sequence[i+1] == 'G' else 'Medium',
                'region': identify_region(i)
            })
        if aa == 'D' and sequence[i+1] in ['G', 'S']:
            ptm_sites['isomerization'].append({
                'position': i,
                'motif': sequence[i:i+2],
                'risk': 'High',
                'region': identify_region(i)
            })

    for i, aa in enumerate(sequence):
        if aa in ['M', 'W']:
            ptm_sites['oxidation'].append({
                'position': i, 'residue': aa,
                'risk': 'Medium', 'region': identify_region(i)
            })

    for i in range(len(sequence)-2):
        if sequence[i] == 'N' and sequence[i+1] != 'P' and sequence[i+2] in ['S', 'T']:
            ptm_sites['glycosylation'].append({
                'position': i,
                'motif': sequence[i:i+3],
                'region': identify_region(i)
            })

    return ptm_sites
```

### 5.3 Developability Scoring

```python
def calculate_developability_score(sequence, structure):
    """Calculate comprehensive developability score (0-100)."""

    scores = {
        'aggregation': score_aggregation(assess_aggregation(sequence)),
        'ptm_liability': score_ptm_risk(identify_ptm_sites(sequence)),
        'stability': score_stability(predict_thermal_stability(structure)),
        'expression': score_expression(predict_expression_level(sequence)),
        'solubility': score_solubility(predict_solubility(sequence))
    }

    weights = {
        'aggregation': 0.30,
        'ptm_liability': 0.25,
        'stability': 0.20,
        'expression': 0.15,
        'solubility': 0.10
    }

    overall = sum(scores[k] * weights[k] for k in scores.keys())

    return {
        'component_scores': scores,
        'overall_score': overall,
        'tier': categorize_developability(overall)
    }
```

---

## Phase 6: Immunogenicity Prediction

### 6.1 T-Cell Epitope Prediction

```python
def predict_tcell_epitopes(tu, sequence):
    """Predict T-cell epitopes using IEDB tools."""

    predicted_epitopes = []

    for i in range(len(sequence) - 8):
        peptide = sequence[i:i+9]

        iedb_results = tu.tools.iedb_search_epitopes(
            sequence_contains=peptide[:5],
            limit=10
        )

        if len(iedb_results) > 0:
            predicted_epitopes.append({
                'position': i,
                'peptide': peptide,
                'risk': 'High',
                'evidence': f"{len(iedb_results)} similar epitopes in IEDB"
            })

    risk_score = calculate_immunogenicity_risk(predicted_epitopes, sequence)

    return {
        'epitope_count': len(predicted_epitopes),
        'high_risk_epitopes': [e for e in predicted_epitopes if e['risk'] == 'High'],
        'risk_score': risk_score,
        'recommendation': recommend_deimmunization(predicted_epitopes)
    }
```

### 6.2 Immunogenicity Risk Scoring

```python
def calculate_immunogenicity_risk(epitopes, sequence):
    """Calculate comprehensive immunogenicity risk score."""

    tcell_score = len(epitopes) * 10
    non_human_score = count_non_human_residues(sequence) * 5
    aggregation_score = assess_aggregation(sequence)['overall_risk'] * 20

    total_risk = min(100, tcell_score + non_human_score + aggregation_score)

    return {
        'tcell_risk': tcell_score,
        'non_human_risk': non_human_score,
        'aggregation_risk': aggregation_score,
        'total_risk': total_risk,
        'category': 'Low' if total_risk < 30 else 'Medium' if total_risk < 60 else 'High'
    }
```

---

## Phase 7: Manufacturing Feasibility

See `MANUFACTURING.md` for detailed manufacturing assessment code and guidance.

### 7.1 Manufacturing Assessment

```python
def assess_manufacturing_feasibility(sequence):
    """Assess manufacturing and CMC feasibility."""

    cho_optimized = optimize_codons(sequence, host='CHO')
    rare_codons = count_rare_codons(sequence, host='CHO')
    signal_peptide = design_signal_peptide(sequence)

    purification = {
        'protein_a_binding': check_protein_a_binding(sequence),
        'ion_exchange': suggest_ion_exchange_conditions(sequence),
        'hydrophobic': suggest_hic_conditions(sequence)
    }

    formulation = {
        'target_concentration': predict_max_concentration(sequence),
        'buffer': suggest_buffer_conditions(sequence),
        'stabilizers': suggest_stabilizers(sequence),
        'shelf_life': predict_shelf_life(sequence)
    }

    return {
        'expression': {'cho_optimized': cho_optimized, 'rare_codons': rare_codons},
        'purification': purification,
        'formulation': formulation
    }
```
