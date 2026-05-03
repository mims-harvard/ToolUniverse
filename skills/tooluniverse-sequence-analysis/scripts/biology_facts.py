"""Reference lookup tool for commonly-tested biology facts.

This is a LOOKUP TOOL, not a memorization aid. Use it to verify facts
rather than guessing — treat it like querying a reference handbook.

Usage:
    python biology_facts.py --type receptor --name "GABAA"
    python biology_facts.py --type receptor --name "GABAB"
    python biology_facts.py --type receptor --name "nicotinic"
    python biology_facts.py --type receptor --name "muscarinic"
    python biology_facts.py --type ion_channel --name "GABAA"
    python biology_facts.py --type ion_channel --name "NMDA"
    python biology_facts.py --type ion_channel --name "AMPA"
    python biology_facts.py --type ion_channel --name "Kv"
    python biology_facts.py --type neurotransmitter --name "GABA"
    python biology_facts.py --type neurotransmitter --name "acetylcholine"
    python biology_facts.py --type immune_cell --name "B cell"
    python biology_facts.py --type immune_cell --name "T helper"
    python biology_facts.py --type immune_cell --name "NK"
    python biology_facts.py --type gene_confusion --name "GABRA1"
    python biology_facts.py --type gene_confusion --name "BRCA1"
    python biology_facts.py --type gene_confusion --name "TP53"
    python biology_facts.py --type receptor          # list all entries
    python biology_facts.py --type ion_channel       # list all entries
    python biology_facts.py --type neurotransmitter  # list all entries
    python biology_facts.py --type immune_cell       # list all entries
    python biology_facts.py --type gene_confusion    # list all entries
"""

import argparse
import sys
from textwrap import dedent

# ---------------------------------------------------------------------------
# DATABASE: receptors
# ---------------------------------------------------------------------------

RECEPTORS: dict[str, dict] = {
    "GABAA": {
        "full_name": "GABA type-A receptor",
        "aliases": ["GABAA", "GABA-A", "GABAAR", "GABA_A"],
        "receptor_class": "Ligand-gated ion channel (ionotropic)",
        "superfamily": "Cys-loop receptor superfamily (pentameric)",
        "stoichiometry": "Pentamer — 5 subunits forming a central ion pore",
        "ion_selectivity": "Cl- (chloride); inhibitory — hyperpolarises the neuron",
        "subunit_families": ["alpha (α1–6)", "beta (β1–3)", "gamma (γ1–3)", "delta (δ)", "epsilon (ε)", "theta (θ)", "pi (π)", "rho (ρ1–3)"],
        "typical_composition": "2α + 2β + 1γ (most common synaptic form, e.g. α1β2γ2)",
        "rho_subunits": (
            "ρ subunits form homomeric or heteromeric pentamers (formerly called GABAC receptors). "
            "ρ1 homomers: 5 identical ρ1 subunits. "
            "Gene: GABRR1 (NOT GABRA1 — a critical naming confusion)."
        ),
        "pharmacology": [
            "Benzodiazepines (diazepam) — positive allosteric modulator at α/γ interface",
            "Barbiturates — positive allosteric modulator (different site from BZD)",
            "Ethanol — facilitates GABA-A function",
            "Picrotoxin — pore blocker (antagonist)",
            "Bicuculline — competitive antagonist at GABA binding site",
            "Muscimol — agonist (from Amanita muscaria)",
        ],
        "key_distinctions": [
            "GABAA is ionotropic (fast, ms timescale); GABAB is metabotropic (slow, GPCR).",
            "Cl- influx causes IPSP (inhibitory post-synaptic potential) in mature neurons.",
            "In immature neurons, Cl- gradient is reversed — GABA-A is EXCITATORY.",
            "GABRR1 gene encodes ρ1 subunit, NOT GABRA1 (which encodes α1).",
        ],
        "gene_names": {
            "α1": "GABRA1",
            "α2": "GABRA2",
            "α3": "GABRA3",
            "α4": "GABRA4",
            "α5": "GABRA5",
            "α6": "GABRA6",
            "β1": "GABRB1",
            "β2": "GABRB2",
            "β3": "GABRB3",
            "γ1": "GABRG1",
            "γ2": "GABRG2",
            "γ3": "GABRG3",
            "δ": "GABRD",
            "ε": "GABRE",
            "ρ1": "GABRR1",
            "ρ2": "GABRR2",
            "ρ3": "GABRR3",
        },
    },
    "GABAB": {
        "full_name": "GABA type-B receptor",
        "aliases": ["GABAB", "GABA-B", "GABABR", "GABA_B"],
        "receptor_class": "Metabotropic receptor (GPCR)",
        "superfamily": "Class C GPCR (same family as mGluRs)",
        "stoichiometry": "Obligatory heterodimer: GABAB1 + GABAB2 subunits",
        "signal_transduction": [
            "Coupled to Gi/Go — inhibits adenylyl cyclase (↓cAMP)",
            "Opens K+ channels (GIRK) → hyperpolarisation",
            "Closes presynaptic voltage-gated Ca2+ channels → reduces neurotransmitter release",
        ],
        "pharmacology": [
            "Baclofen — selective agonist (clinically used for muscle spasticity)",
            "CGP35348 — antagonist",
            "Phaclofen — antagonist",
        ],
        "key_distinctions": [
            "NOT a ligand-gated ion channel — it is a GPCR. A common exam error is treating GABAB like GABAA.",
            "Effects are slow (seconds) versus GABAA (milliseconds).",
            "Baclofen acts at GABAB, not GABAA.",
            "Benzodiazepines have NO effect on GABAB.",
        ],
        "gene_names": {"GABAB1": "GABBR1", "GABAB2": "GABBR2"},
    },
    "nicotinic": {
        "full_name": "Nicotinic acetylcholine receptor (nAChR)",
        "aliases": ["nicotinic", "nAChR", "nicotinic AChR", "nicotinic acetylcholine receptor"],
        "receptor_class": "Ligand-gated ion channel (ionotropic)",
        "superfamily": "Cys-loop receptor superfamily (pentameric)",
        "stoichiometry": "Pentamer — 5 subunits",
        "ion_selectivity": "Na+ (and Ca2+); cation channel — depolarises the membrane (excitatory)",
        "subunit_families": [
            "Muscle type: α1, β1, γ, δ, ε (adult: 2α1 + β1 + δ + ε; fetal: 2α1 + β1 + γ + δ)",
            "Neuronal: α2–α10, β2–β4",
            "α7 homomeric is a key neuronal subtype (high Ca2+ permeability)",
        ],
        "pharmacology": [
            "Nicotine — agonist",
            "Acetylcholine — endogenous agonist",
            "Succinylcholine — depolarising neuromuscular blocker",
            "Tubocurarine (curare) — competitive antagonist at NMJ",
            "Mecamylamine — neuronal nAChR antagonist",
            "α-Bungarotoxin — irreversible antagonist (binds α1-type at NMJ and α7)",
        ],
        "locations": ["Neuromuscular junction (NMJ)", "Autonomic ganglia", "Brain (α4β2 most abundant neuronal form)", "Adrenal medulla"],
        "key_distinctions": [
            "Cation channel (Na+/K+/Ca2+) — always excitatory (unlike GABAA which is Cl-).",
            "Different from muscarinic AChR (which is a GPCR, not ion channel).",
            "α7 homomeric nAChR: 5 identical α7 subunits — important for CNS function and Ca2+ signalling.",
        ],
    },
    "muscarinic": {
        "full_name": "Muscarinic acetylcholine receptor (mAChR)",
        "aliases": ["muscarinic", "mAChR", "muscarinic AChR", "muscarinic acetylcholine receptor"],
        "receptor_class": "Metabotropic receptor (GPCR)",
        "superfamily": "Class A GPCR (rhodopsin-like)",
        "subtypes": {
            "M1": "Gq-coupled; CNS, gastric parietal cells; atropine antagonist",
            "M2": "Gi-coupled; heart (slows heart rate); cardiac effects",
            "M3": "Gq-coupled; smooth muscle, glands; bronchospasm",
            "M4": "Gi-coupled; CNS, striatum",
            "M5": "Gq-coupled; CNS (dopaminergic neurons)",
        },
        "pharmacology": [
            "Muscarine — agonist (from mushrooms, gives name)",
            "Acetylcholine — endogenous agonist",
            "Atropine — nonselective competitive antagonist",
            "Scopolamine — CNS-penetrant antagonist (antiemetic)",
            "Pirenzepine — M1-selective antagonist",
            "Ipratropium — M3 antagonist (bronchodilator)",
        ],
        "key_distinctions": [
            "GPCR, NOT an ion channel. Always confuse with nicotinic receptor at your peril.",
            "Effects are slower and more varied than nicotinic (via second messengers).",
            "M2 slows the heart — contrast with nicotinic NMJ which accelerates (excitatory) muscle contraction.",
        ],
    },
    "NMDA": {
        "full_name": "N-methyl-D-aspartate receptor",
        "aliases": ["NMDA", "NMDAR", "NR"],
        "receptor_class": "Ligand-gated ion channel (ionotropic)",
        "superfamily": "Ionotropic glutamate receptor (iGluR)",
        "stoichiometry": "Heterotetramer — 2 GluN1 + 2 GluN2 (or 1 GluN2 + 1 GluN3) subunits",
        "ion_selectivity": "Ca2+, Na+, K+ (high Ca2+ permeability distinguishes it from AMPA)",
        "activation_requirements": [
            "Glutamate binding (at GluN2 subunit)",
            "Glycine/D-serine binding (co-agonist at GluN1 subunit) — REQUIRED",
            "Membrane depolarisation to relieve Mg2+ block (voltage-dependent Mg2+ block at rest)",
        ],
        "pharmacology": [
            "AP5 (APV) — competitive antagonist",
            "MK-801 (dizocilpine) — open-channel blocker",
            "Ketamine — open-channel blocker (anaesthetic/antidepressant)",
            "Memantine — uncompetitive antagonist (Alzheimer's drug)",
            "Mg2+ — voltage-dependent pore block (endogenous)",
            "PCP (phencyclidine) — open-channel blocker",
        ],
        "key_distinctions": [
            "Tetrameric (4 subunits), NOT pentameric like GABA-A or nicotinic.",
            "Requires BOTH glutamate AND glycine to open (coincidence detector).",
            "Mg2+ block at resting potential — removes only upon depolarisation (Hebbian plasticity mechanism).",
            "High Ca2+ permeability mediates LTP and excitotoxicity.",
        ],
    },
    "AMPA": {
        "full_name": "AMPA receptor",
        "aliases": ["AMPA", "AMPAR"],
        "receptor_class": "Ligand-gated ion channel (ionotropic)",
        "superfamily": "Ionotropic glutamate receptor (iGluR)",
        "stoichiometry": "Heterotetramer — combinations of GluA1–4 subunits",
        "ion_selectivity": "Na+, K+ (and Ca2+ if lacking GluA2 subunit)",
        "subunit_note": (
            "GluA2 subunit contains a critical RNA-editing site (Q/R site): "
            "unedited Q (glutamine) → Ca2+-permeable; edited R (arginine) → Ca2+-impermeable. "
            "Most adult neurons express edited GluA2 → NOT Ca2+-permeable under normal conditions."
        ),
        "pharmacology": [
            "CNQX — competitive antagonist (blocks both AMPA and kainate)",
            "NBQX — selective AMPA antagonist",
            "AMPA — agonist (gives receptor its name)",
        ],
        "key_distinctions": [
            "Tetrameric (4 subunits), NOT pentameric.",
            "Faster kinetics than NMDA — mediates fast excitatory neurotransmission.",
            "Does NOT require co-agonist (unlike NMDA which needs glycine).",
            "No Mg2+ block (unlike NMDA).",
            "Ca2+ permeability depends on GluA2 editing — this is a very common exam topic.",
        ],
    },
}

# ---------------------------------------------------------------------------
# DATABASE: ion channels (stoichiometry focus)
# ---------------------------------------------------------------------------

ION_CHANNELS: dict[str, dict] = {
    "GABAA": {
        "full_name": "GABA-A receptor / Cl- channel",
        "aliases": ["GABAA", "GABA-A", "GABAAR"],
        "stoichiometry": "Pentamer (5 subunits)",
        "subunit_arrangement": "Pseudo-5-fold symmetry around central Cl- pore",
        "rho_homomers": "ρ subunit homomers: 5 identical ρ subunits (e.g. ρ1 homomer = 5× ρ1)",
        "ion": "Cl- (influx; inhibitory in mature neurons)",
        "superfamily": "Cys-loop receptor",
        "note": "Each subunit contributes the M2 transmembrane segment to line the channel pore.",
    },
    "nicotinic AChR": {
        "full_name": "Nicotinic acetylcholine receptor",
        "aliases": ["nicotinic", "nAChR", "nicotinic AChR"],
        "stoichiometry": "Pentamer (5 subunits)",
        "subunit_arrangement": "α2βγδ (fetal NMJ) or α2βεδ (adult NMJ); α4β2 (neuronal, 2:3 ratio common); α7 homomer (5× α7)",
        "ion": "Na+, K+, Ca2+ (cation channel; excitatory)",
        "superfamily": "Cys-loop receptor",
        "note": "Like GABA-A, belongs to the pentameric Cys-loop family despite opposite function (excitatory vs inhibitory).",
    },
    "NMDA": {
        "full_name": "NMDA receptor / Ca2+ channel",
        "aliases": ["NMDA", "NMDAR"],
        "stoichiometry": "Heterotetramer (4 subunits)",
        "subunit_arrangement": "2× GluN1 + 2× GluN2 (most common), or 2× GluN1 + 1× GluN2 + 1× GluN3",
        "ion": "Ca2+, Na+, K+ (high Ca2+ permeability; excitatory)",
        "superfamily": "Ionotropic glutamate receptor (iGluR)",
        "note": "Common error: calling it pentameric. It is TETRAMERIC like all iGluRs.",
    },
    "AMPA": {
        "full_name": "AMPA receptor",
        "aliases": ["AMPA", "AMPAR"],
        "stoichiometry": "Heterotetramer (4 subunits)",
        "subunit_arrangement": "GluA1–4 in various combinations; GluA1/2 and GluA2/3 most common in hippocampus",
        "ion": "Na+, K+ (and Ca2+ if GluA2 absent or unedited)",
        "superfamily": "Ionotropic glutamate receptor (iGluR)",
        "note": "Tetrameric. Fastest of the major glutamate receptor types.",
    },
    "Kv": {
        "full_name": "Voltage-gated potassium channel",
        "aliases": ["Kv", "Kv channel", "voltage-gated K+", "voltage-gated potassium"],
        "stoichiometry": "Tetramer (4 alpha subunits)",
        "subunit_arrangement": "4 identical (homotetrameric) or 4 different (heterotetrameric) alpha subunits; each has 6 TM segments (S1–S6); S4 is voltage sensor; S5–S6 form the pore",
        "ion": "K+ (outward; repolarisation of action potential)",
        "superfamily": "Voltage-gated ion channel superfamily",
        "note": "Tetrameric architecture is also shared by Nav and Cav, but those are single polypeptides with 4 internally repeated domains (pseudo-tetramers).",
    },
    "Nav": {
        "full_name": "Voltage-gated sodium channel",
        "aliases": ["Nav", "Na+ channel", "voltage-gated Na+", "voltage-gated sodium"],
        "stoichiometry": "Single alpha subunit (pseudo-tetramer) + 1–2 beta subunits",
        "subunit_arrangement": "One large alpha subunit with 4 homologous domains (I–IV), each with 6 TM segments. NOT 4 separate subunits.",
        "ion": "Na+ (inward; depolarisation of action potential)",
        "superfamily": "Voltage-gated ion channel superfamily",
        "note": "Common error: calling it a 'tetramer of subunits' like Kv. It is a single polypeptide with 4 repeated domains.",
    },
    "Cav": {
        "full_name": "Voltage-gated calcium channel",
        "aliases": ["Cav", "Ca2+ channel", "voltage-gated Ca2+", "voltage-gated calcium", "VGCC"],
        "stoichiometry": "Alpha1 subunit (pseudo-tetramer) + auxiliary subunits (alpha2-delta, beta, gamma)",
        "subunit_arrangement": "Same 4-domain architecture as Nav. Alpha1 is the pore-forming subunit.",
        "ion": "Ca2+ (inward; triggers neurotransmitter release, muscle contraction, signalling)",
        "subtypes": "L-type (Cav1), P/Q-type (Cav2.1), N-type (Cav2.2), R-type (Cav2.3), T-type (Cav3)",
        "superfamily": "Voltage-gated ion channel superfamily",
        "note": "Not a true heterotetramer — the four domains are within a single polypeptide.",
    },
    "CFTR": {
        "full_name": "Cystic fibrosis transmembrane conductance regulator",
        "aliases": ["CFTR", "ABCC7"],
        "stoichiometry": "Monomer (single polypeptide)",
        "subunit_arrangement": "2 membrane-spanning domains (MSD1/2) + 2 nucleotide-binding domains (NBD1/2) + 1 regulatory (R) domain",
        "ion": "Cl- (and HCO3-); activated by PKA phosphorylation + ATP binding",
        "superfamily": "ABC transporter superfamily (ABC-C subfamily)",
        "note": "Unique among Cl- channels — it is an ATP-gated channel, not a ligand-gated or voltage-gated channel. Mutated in cystic fibrosis (F508del is the most common mutation).",
    },
}

# ---------------------------------------------------------------------------
# DATABASE: neurotransmitters
# ---------------------------------------------------------------------------

NEUROTRANSMITTERS: dict[str, dict] = {
    "GABA": {
        "full_name": "Gamma-aminobutyric acid",
        "aliases": ["GABA", "gamma-aminobutyric acid", "γ-aminobutyric acid"],
        "type": "Amino acid (inhibitory)",
        "synthesis": "Glutamate → GABA via glutamate decarboxylase (GAD; requires PLP/vitamin B6)",
        "degradation": "GABA-T (GABA transaminase) → succinic semialdehyde → enters TCA cycle",
        "receptors": {
            "GABAA": "Ionotropic, Cl- channel, fast inhibition (ms)",
            "GABAB": "Metabotropic GPCR (Gi/Go), slow inhibition (s); K+ channel opening, Ca2+ channel closing",
            "GABAC": "Ionotropic (rho subunits); now classified as GABAA-rho",
        },
        "function": "Primary inhibitory neurotransmitter in the brain; counterbalances glutamate excitation",
        "key_distinctions": [
            "GABA itself is NOT directly inhibitory — it acts via its receptors.",
            "In immature neurons, GABA-A is EXCITATORY (high intracellular Cl- due to low KCC2 expression).",
            "GAD67 and GAD65 are two isoforms of GAD; both are markers for GABAergic neurons.",
            "Vigabatrin inhibits GABA-T (↑GABA levels); used for epilepsy.",
        ],
    },
    "glutamate": {
        "full_name": "Glutamate (glutamic acid)",
        "aliases": ["glutamate", "Glu", "glutamic acid"],
        "type": "Amino acid (excitatory)",
        "synthesis": "From alpha-ketoglutarate (TCA cycle) via transamination, or from glutamine via glutaminase",
        "degradation": "Reuptake into neurons/astrocytes; converted to glutamine in astrocytes (glutamine synthetase)",
        "receptors": {
            "AMPA": "Ionotropic (iGluR), fast excitation, Na+/K+",
            "NMDA": "Ionotropic (iGluR), slow/coincidence, Ca2+/Na+/K+; needs glycine co-agonist",
            "Kainate": "Ionotropic (iGluR), Na+/K+",
            "mGluR1/5": "Metabotropic, Gq-coupled (group I)",
            "mGluR2/3": "Metabotropic, Gi-coupled (group II, presynaptic autoreceptors)",
            "mGluR4/6/7/8": "Metabotropic, Gi-coupled (group III)",
        },
        "function": "Primary excitatory neurotransmitter; essential for LTP, learning, memory",
        "key_distinctions": [
            "Excitotoxicity: excessive glutamate → overactivation of NMDA → Ca2+ overload → cell death.",
            "Glutamate is also a precursor for GABA (via GAD).",
        ],
    },
    "acetylcholine": {
        "full_name": "Acetylcholine",
        "aliases": ["acetylcholine", "ACh", "Ach"],
        "type": "Ester (cholinergic)",
        "synthesis": "Choline + Acetyl-CoA → ACh via choline acetyltransferase (ChAT)",
        "degradation": "Acetylcholinesterase (AChE) → choline + acetate (at synapse); choline recycled",
        "receptors": {
            "Nicotinic (nAChR)": "Ionotropic, pentameric, Na+/Ca2+; fast (NMJ, ganglia, CNS)",
            "Muscarinic (mAChR)": "Metabotropic GPCR, M1–M5; slow (heart, smooth muscle, glands, CNS)",
        },
        "function": "Neuromuscular junction, autonomic nervous system, CNS memory circuits (basal forebrain)",
        "key_distinctions": [
            "nAChR (ionotropic) vs mAChR (GPCR) — same ligand, completely different receptor families.",
            "AChE inhibitors (neostigmine, physostigmine, donepezil) increase ACh levels.",
            "Organophosphate poisoning: irreversible AChE inhibition → SLUD symptoms (Salivation, Lacrimation, Urination, Defecation) + muscle paralysis.",
        ],
    },
    "dopamine": {
        "full_name": "Dopamine",
        "aliases": ["dopamine", "DA", "3,4-dihydroxyphenethylamine"],
        "type": "Catecholamine (monoamine)",
        "synthesis": "Tyrosine → L-DOPA (via TH) → Dopamine (via AADC/DOPA decarboxylase)",
        "degradation": "MAO (monoamine oxidase) and COMT → homovanillic acid (HVA); reuptake via DAT",
        "receptors": {
            "D1, D5": "Gs-coupled GPCRs → ↑cAMP",
            "D2, D3, D4": "Gi-coupled GPCRs → ↓cAMP",
        },
        "function": "Reward, motivation, motor control (striatum), working memory (prefrontal cortex)",
        "key_distinctions": [
            "Parkinson's: loss of dopaminergic neurons in substantia nigra pars compacta (SNpc).",
            "L-DOPA (not dopamine itself) crosses the blood-brain barrier — used in Parkinson's treatment.",
            "D2 receptor blockade is the mechanism of antipsychotic drugs.",
        ],
    },
    "serotonin": {
        "full_name": "Serotonin (5-hydroxytryptamine)",
        "aliases": ["serotonin", "5-HT", "5-hydroxytryptamine"],
        "type": "Indoleamine (monoamine)",
        "synthesis": "Tryptophan → 5-HTP (via tryptophan hydroxylase) → Serotonin (via AADC)",
        "degradation": "MAO-A → 5-HIAA; reuptake via SERT",
        "receptors": {
            "5-HT3": "Ionotropic (Cys-loop pentamer); Na+/K+; fast; nausea/vomiting circuit",
            "5-HT1A, 1B, 1D": "Gi-coupled GPCRs; anxiolytic, autoreceptors",
            "5-HT2A, 2C": "Gq-coupled GPCRs; psychedelics target 5-HT2A",
            "5-HT4, 6, 7": "Gs-coupled GPCRs",
        },
        "function": "Mood, sleep, appetite, gut motility (90% of body's serotonin is in the gut)",
        "key_distinctions": [
            "5-HT3 is the ONLY ionotropic serotonin receptor (the others are GPCRs).",
            "SSRIs block SERT — increase synaptic serotonin.",
            "Ondansetron (antiemetic) is a 5-HT3 antagonist.",
        ],
    },
    "glycine": {
        "full_name": "Glycine",
        "aliases": ["glycine", "Gly"],
        "type": "Amino acid (inhibitory in spinal cord; co-agonist at NMDA in brain)",
        "synthesis": "Serine → Glycine via serine hydroxymethyltransferase (SHMT)",
        "degradation": "Glycine cleavage system; reuptake via GlyT1/GlyT2",
        "receptors": {
            "Glycine receptor (GlyR)": "Ionotropic, Cys-loop pentamer, Cl- (inhibitory; spinal cord and brainstem)",
            "NMDA receptor (GluN1 site)": "Co-agonist; binding is required for NMDA channel opening (in addition to glutamate)",
        },
        "function": "Inhibitory neurotransmitter in spinal cord/brainstem; NMDA co-agonist in brain",
        "key_distinctions": [
            "Strychnine blocks glycine receptors → convulsions.",
            "At NMDA receptors, D-serine (not glycine) may be the predominant co-agonist in cortex.",
            "GlyT1 inhibitors in development for schizophrenia (boost NMDA via ↑glycine).",
        ],
    },
}

# ---------------------------------------------------------------------------
# DATABASE: immune cells
# ---------------------------------------------------------------------------

IMMUNE_CELLS: dict[str, dict] = {
    "B cell": {
        "full_name": "B lymphocyte",
        "aliases": ["B cell", "B lymphocyte", "B-cell", "B lymph"],
        "lineage": "Lymphoid; adaptive immunity",
        "origin_maturation": "Bone marrow (develops and matures); periphery (activation in lymph nodes/spleen)",
        "key_markers": ["CD19 (pan-B marker)", "CD20 (mature B cells; target of rituximab)", "CD21", "CD22", "MHCII", "B220/CD45R (mice)", "surface immunoglobulin (BCR)"],
        "function": "Produce antibodies (immunoglobulins); antigen presentation",
        "subtypes": {
            "Naive B cell": "Has not encountered antigen; expresses IgM/IgD",
            "Plasma cell": "Terminally differentiated antibody factory; high Ig secretion; low surface CD20",
            "Memory B cell": "Long-lived; rapid response upon re-exposure",
            "B1 cell": "Innate-like; T-independent responses; produces natural IgM",
            "Marginal zone B cell": "In spleen; responds quickly to blood-borne T-independent antigens",
        },
        "key_distinctions": [
            "CD19 is the broadest B-cell marker (also present on plasma cell precursors).",
            "CD20 is absent from plasma cells and very early pro-B cells.",
            "B cells do NOT kill targets directly — they make antibodies (contrast with cytotoxic T cells).",
            "T helper cells are required for B-cell activation in T-dependent responses.",
        ],
    },
    "T helper": {
        "full_name": "T helper cell (CD4+ T cell)",
        "aliases": ["T helper", "Th cell", "CD4+ T cell", "T helper cell", "helper T"],
        "lineage": "Lymphoid; adaptive immunity",
        "origin_maturation": "Thymus (develops from common lymphoid progenitor)",
        "key_markers": ["CD4 (defines subset)", "CD3 (pan-T)", "TCR", "CD45RO (memory)", "CD45RA (naive)"],
        "function": "Coordinate immune responses; help B cells make antibodies; activate macrophages; promote cytotoxic T cells",
        "subtypes": {
            "Th1": "IFN-γ; cellular immunity; fights intracellular pathogens; activates macrophages",
            "Th2": "IL-4, IL-5, IL-13; humoral immunity, allergy, parasites; helps B cells class switch to IgE",
            "Th17": "IL-17; mucosal immunity; fights extracellular bacteria/fungi; autoimmunity",
            "Treg": "FoxP3+; suppresses other immune cells; self-tolerance",
            "Tfh": "CXCR5+; follicular; provides B cell help in germinal centres",
        },
        "key_distinctions": [
            "CD4 binds MHCII — T helpers recognise antigen presented on MHCII (vs CD8 T cells on MHCI).",
            "HIV infects CD4+ T cells (via CD4 + CCR5/CXCR4).",
            "Th cells CANNOT kill directly — they coordinate via cytokines and cell contact (CD40L–CD40).",
        ],
    },
    "T cytotoxic": {
        "full_name": "Cytotoxic T lymphocyte (CD8+ T cell)",
        "aliases": ["T cytotoxic", "CTL", "CD8+ T cell", "cytotoxic T", "killer T cell", "Tc cell"],
        "lineage": "Lymphoid; adaptive immunity",
        "origin_maturation": "Thymus",
        "key_markers": ["CD8 (defines subset)", "CD3 (pan-T)", "TCR", "Granzyme B", "Perforin"],
        "function": "Directly kill virus-infected cells, tumour cells; via perforin/granzyme pathway or Fas/FasL",
        "killing_mechanisms": [
            "Perforin: pore-forming protein punches holes in target cell membrane",
            "Granzymes (A, B): serine proteases delivered via perforin pores → activate caspases → apoptosis",
            "Fas/FasL: surface interaction triggers apoptosis in Fas-expressing target cells",
        ],
        "key_distinctions": [
            "CD8 binds MHCI — CTLs recognise peptides presented on MHCI (all nucleated cells express MHCI).",
            "Virus-infected cells downregulate MHCI to hide from CTLs — NK cells detect MISSING MHCI.",
            "CD8 vs CD4: CD8 = cytotoxic/kill; CD4 = helper/coordinate. Memory aid: 4 > 8 → helper is 'larger number concept' group that helps.",
        ],
    },
    "NK": {
        "full_name": "Natural killer cell",
        "aliases": ["NK", "NK cell", "natural killer", "natural killer cell"],
        "lineage": "Lymphoid; innate immunity",
        "origin_maturation": "Bone marrow; circulates in blood and lymphoid tissues",
        "key_markers": ["CD56 (NCAM; defines NK cells)", "CD16 (FcγRIII; mediates ADCC)", "CD3-negative (no TCR)", "NKp46", "NKG2D"],
        "function": "Kill virus-infected and tumour cells without prior sensitisation; ADCC; cytokine production (IFN-γ)",
        "activation_mechanism": [
            "Missing-self: target cells lacking MHCI activate NK cells (vs CTLs which need MHCI + peptide)",
            "Stress ligands: NKG2D recognises MICA/MICB on stressed/transformed cells",
            "ADCC: CD16 binds Fc region of antibodies coating target cells",
        ],
        "key_distinctions": [
            "NO TCR, NO BCR — NOT part of adaptive immunity.",
            "CD3-negative distinguishes NK from T cells (which are CD3+).",
            "NK cells kill cells with ABSENT MHCI; CTLs kill cells with PRESENT MHCI (+ specific peptide).",
            "CD56bright NK cells are immunoregulatory; CD56dim CD16+ are cytotoxic.",
        ],
    },
    "macrophage": {
        "full_name": "Macrophage",
        "aliases": ["macrophage", "Mphi", "M1", "M2"],
        "lineage": "Myeloid; innate immunity (also adaptive antigen presentation)",
        "origin_maturation": "Monocytes from bone marrow → tissues; or tissue-resident (from yolk sac/fetal liver)",
        "key_markers": ["CD68 (pan-macrophage)", "CD11b", "CD14", "MHCIIs", "F4/80 (mice)", "CD64"],
        "function": "Phagocytosis, antigen presentation (MHCII), cytokine production, tissue remodelling",
        "polarisation": {
            "M1 (classically activated)": "IFN-γ/LPS stimulus; pro-inflammatory; TNF, IL-1β, IL-6, IL-12; antimicrobial; ROS/RNS",
            "M2 (alternatively activated)": "IL-4/IL-13 stimulus; anti-inflammatory; IL-10, TGF-β; tissue repair, fibrosis",
        },
        "key_distinctions": [
            "Macrophages can present antigen via MHCII (like B cells and DCs) — this is how they activate CD4+ T cells.",
            "CD68 is the canonical pan-macrophage marker; CD68+ cells in tissue = macrophages.",
            "Microglia (brain macrophages) are CD68+/Iba1+/TMEM119+.",
        ],
    },
    "dendritic cell": {
        "full_name": "Dendritic cell (DC)",
        "aliases": ["dendritic cell", "DC", "plasmacytoid DC", "pDC", "conventional DC", "cDC"],
        "lineage": "Myeloid (cDC) or lymphoid-related (pDC); innate/adaptive bridge",
        "origin_maturation": "Bone marrow; immature in tissues → mature in lymph nodes after antigen capture",
        "key_markers": ["CD11c (major DC marker)", "MHC I + II", "CD80, CD86 (co-stimulation)", "CD83 (mature DC)", "BDCA-1/2/3 (human subtypes)"],
        "function": "Professional antigen-presenting cells (APCs); bridge innate and adaptive immunity; activate naive T cells",
        "subtypes": {
            "cDC1 (CD8a+/CD103+)": "Cross-presents antigens; activates CD8 T cells; IL-12 producing",
            "cDC2 (CD11b+)": "Activates CD4 T cells; responds to extracellular pathogens",
            "pDC": "Plasmacytoid; major IFN-α/β producers; antiviral innate immunity",
        },
        "key_distinctions": [
            "The BEST professional APC for activating NAIVE T cells (vs B cells and macrophages which can also present).",
            "Cross-presentation by cDC1 allows CD8 T cell activation against extracellular antigens.",
        ],
    },
    "neutrophil": {
        "full_name": "Neutrophil (polymorphonuclear leukocyte)",
        "aliases": ["neutrophil", "PMN", "polymorphonuclear", "granulocyte"],
        "lineage": "Myeloid; innate immunity",
        "origin_maturation": "Bone marrow granulopoiesis; short-lived (~hours to days)",
        "key_markers": ["CD66b", "CD16 (FcγRIII)", "CD11b", "MPO (myeloperoxidase)", "Ly6G (mouse)"],
        "function": "First responders to infection; phagocytosis; degranulation; NET formation",
        "killing_mechanisms": [
            "Oxidative burst (NADPH oxidase → superoxide → ROS)",
            "Degranulation (elastase, MPO, defensins)",
            "NETs (Neutrophil Extracellular Traps): chromatin + antimicrobial proteins",
        ],
        "key_distinctions": [
            "Most abundant white blood cell in peripheral blood (~50–70%).",
            "Multi-lobed (2–5 lobes) nucleus — this is how they are identified by morphology.",
            "Unlike macrophages, neutrophils are NOT effective antigen presenters.",
        ],
    },
}

# ---------------------------------------------------------------------------
# DATABASE: gene confusions
# ---------------------------------------------------------------------------

GENE_CONFUSION: dict[str, dict] = {
    "GABRA1": {
        "gene_symbol": "GABRA1",
        "encodes": "GABA-A receptor alpha-1 subunit",
        "protein": "GABRA1 protein (alpha-1 subunit of GABA type-A receptor)",
        "locus": "5q34",
        "commonly_confused_with": "GABRR1",
        "confusion_note": (
            "GABRA1 = alpha-1. GABRR1 = rho-1. "
            "Both are GABA-A subunit genes but completely different subunit families. "
            "The 'A' in GABRA stands for alpha; the 'R' in GABRR stands for rho. "
            "Rho subunits form the GABAA-rho receptor (formerly GABAC)."
        ),
        "gene_family": ["GABRA1", "GABRA2", "GABRA3", "GABRA4", "GABRA5", "GABRA6"],
    },
    "GABRR1": {
        "gene_symbol": "GABRR1",
        "encodes": "GABA-A receptor rho-1 subunit",
        "protein": "GABRR1 protein (rho-1 subunit; forms homomeric/heteromeric GABAA-rho receptors)",
        "locus": "6q15",
        "commonly_confused_with": "GABRA1",
        "confusion_note": (
            "GABRR1 = rho-1. GABRA1 = alpha-1. "
            "A homomeric ρ1 receptor is formed by 5 GABRR1-encoded subunits, NOT GABRA1. "
            "GABRR1 homomers and heteromers (ρ1+ρ2, ρ1+ρ3) are found in retina."
        ),
        "gene_family": ["GABRR1", "GABRR2", "GABRR3"],
    },
    "BRCA1": {
        "gene_symbol": "BRCA1",
        "encodes": "Breast cancer type 1 susceptibility protein",
        "protein": "BRCA1 — E3 ubiquitin ligase, DNA damage response, HR repair",
        "locus": "17q21.31",
        "key_facts": [
            "Involved in homologous recombination (HR) DNA repair",
            "Forms BRCA1-BARD1 heterodimer (required for E3 ubiquitin ligase activity)",
            "Pathogenic variants: increased risk of breast cancer (~50–70% lifetime) and ovarian cancer (~30–40%)",
            "BRCA1-mutant tumours are HR-deficient → sensitive to PARP inhibitors (olaparib)",
        ],
        "commonly_confused_with": "BRCA2",
        "confusion_note": (
            "BRCA1 and BRCA2 both increase breast/ovarian cancer risk but via different mechanisms. "
            "BRCA1 (chr 17): E3 ligase, HR. BRCA2 (chr 13): RAD51 mediator, HR. "
            "BRCA2 has higher lifetime ovarian cancer risk (~40–50% vs ~30–40%). "
            "BRCA1 mutations also confer triple-negative breast cancer phenotype more often."
        ),
    },
    "BRCA2": {
        "gene_symbol": "BRCA2",
        "encodes": "Breast cancer type 2 susceptibility protein",
        "protein": "BRCA2 — RAD51 recombinase mediator, HR repair",
        "locus": "13q12.3",
        "key_facts": [
            "Loads RAD51 onto ssDNA for strand invasion in HR",
            "No E3 ubiquitin ligase activity (unlike BRCA1)",
            "Pathogenic variants: breast cancer (~45–65%), ovarian cancer (~40–50%), pancreatic, prostate",
            "Also HR-deficient → PARP inhibitor sensitivity",
        ],
        "commonly_confused_with": "BRCA1",
        "confusion_note": (
            "BRCA2 (chr 13) encodes a RAD51 mediator. BRCA1 (chr 17) encodes an E3 ligase. "
            "Both participate in HR but at distinct steps. "
            "Fanconi anaemia: biallelic BRCA2 mutations = FA complementation group D1 (FANCD1)."
        ),
    },
    "TP53": {
        "gene_symbol": "TP53",
        "encodes": "Tumour protein p53",
        "protein": "p53 — transcription factor; master guardian of the genome",
        "locus": "17p13.1",
        "key_facts": [
            "Most commonly mutated gene in human cancer (~50% of all tumours)",
            "Tetrameric transcription factor — 4 subunits, each with a DNA-binding domain",
            "Activates: CDKN1A (p21; cell cycle arrest), MDM2 (negative feedback), BAX (apoptosis), PUMA, NOXA",
            "MDM2 is the E3 ligase that ubiquitylates p53 for proteasomal degradation",
            "Li-Fraumeni syndrome: germline TP53 mutations",
        ],
        "commonly_confused_with": ["TP63", "TP73"],
        "confusion_note": (
            "TP53, TP63, and TP73 are paralogs — all encode p53-family transcription factors. "
            "TP53 (chr 17): main tumour suppressor. "
            "TP63 (chr 3): epithelial development (skin, limb); not commonly mutated in cancer. "
            "TP73 (chr 1): neuronal; less commonly mutated; ΔNp73 can inhibit p53. "
            "p53 protein is ENCODED by TP53 — note lowercase 'p' for protein, uppercase for gene."
        ),
    },
    "TP63": {
        "gene_symbol": "TP63",
        "encodes": "Tumour protein p63",
        "protein": "p63 — transcription factor, p53 family member; role in epithelial development",
        "locus": "3q27-q29",
        "key_facts": [
            "Essential for stratified epithelial development (skin, oral mucosa, limb formation)",
            "TAp63 isoforms: pro-apoptotic; ΔNp63 isoforms: dominant-negative, promotes proliferation",
            "Marker for squamous cell carcinoma (p63 immunohistochemistry)",
            "EEC syndrome (Ectrodactyly-Ectodermal dysplasia-Clefting): TP63 mutations",
        ],
        "commonly_confused_with": "TP53",
        "confusion_note": (
            "TP63 is NOT a major tumour suppressor in most cancers — that role belongs to TP53. "
            "p63 is used as an IHC marker for basal cells and squamous differentiation."
        ),
    },
    "ALK": {
        "gene_symbol": "ALK",
        "encodes": "Anaplastic lymphoma kinase",
        "protein": "ALK — receptor tyrosine kinase",
        "locus": "2p23.2-p23.1",
        "key_facts": [
            "EML4-ALK fusion: most common ALK rearrangement in non-small cell lung cancer (NSCLC; ~5%)",
            "NPM-ALK fusion: in anaplastic large cell lymphoma (ALCL)",
            "Inhibited by crizotinib, alectinib, lorlatinib (ALK inhibitors)",
            "ALK amplification also occurs in neuroblastoma",
        ],
        "commonly_confused_with": "RET, ROS1",
        "confusion_note": (
            "ALK, RET, and ROS1 are all receptor tyrosine kinases that can be activated by fusion in NSCLC. "
            "Crizotinib was originally developed as MET inhibitor, later found to also inhibit ALK and ROS1."
        ),
    },
    "EGFR": {
        "gene_symbol": "EGFR",
        "encodes": "Epidermal growth factor receptor",
        "protein": "EGFR (HER1/ErbB1) — receptor tyrosine kinase",
        "locus": "7p11.2",
        "key_facts": [
            "HER family: EGFR (HER1), HER2 (ERBB2), HER3 (ERBB3), HER4 (ERBB4)",
            "Common activating mutations in NSCLC: exon 19 deletion, L858R (exon 21)",
            "T790M: resistance mutation to first/second-generation EGFR inhibitors",
            "Inhibitors: gefitinib, erlotinib (1st gen); afatinib (2nd gen); osimertinib (3rd gen, overcomes T790M)",
        ],
        "commonly_confused_with": "HER2 (ERBB2)",
        "confusion_note": (
            "EGFR = HER1 = ERBB1. HER2 = ERBB2 (chromosome 17q). "
            "Trastuzumab (Herceptin) targets HER2, NOT EGFR. "
            "Cetuximab targets EGFR (HER1), NOT HER2."
        ),
    },
    "KRAS": {
        "gene_symbol": "KRAS",
        "encodes": "Kirsten rat sarcoma viral proto-oncogene",
        "protein": "KRAS — small GTPase (Ras family)",
        "locus": "12p12.1",
        "key_facts": [
            "Most frequently mutated RAS gene in human cancer (~85% of RAS mutations)",
            "Hotspots: G12D, G12V, G12C, G13D",
            "KRAS G12C is targetable: sotorasib (AMG-510), adagrasib — first direct KRAS inhibitors",
            "KRAS mutation predicts LACK of response to anti-EGFR antibodies (cetuximab, panitumumab) in colorectal cancer",
            "Oncogenic mutations impair GTPase activity — lock KRAS in GTP-bound (active) state",
        ],
        "commonly_confused_with": ["NRAS", "HRAS"],
        "confusion_note": (
            "KRAS, NRAS, HRAS all encode RAS GTPases. In colorectal cancer, KRAS and NRAS mutations "
            "predict anti-EGFR resistance. HRAS mutations are less common in colorectal cancer. "
            "NRAS mutations are the predominant RAS mutations in melanoma."
        ),
    },
}

# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------


def _resolve_key(name: str, db: dict) -> str | None:
    """Return the canonical db key matching *name* (case-insensitive, alias-aware).

    Returns None when no match is found.
    """
    if name in db:
        return name
    name_lower = name.lower()
    for k, entry in db.items():
        if k.lower() == name_lower:
            return k
        if any(a.lower() == name_lower for a in entry.get("aliases", [])):
            return k
    return None


def _lookup_receptor(name: str) -> None:
    key = _resolve_key(name, RECEPTORS)
    if key is None:
        print(f"ERROR: No receptor entry for '{name}'.", file=sys.stderr)
        print("Available entries:", file=sys.stderr)
        for r in sorted(RECEPTORS):
            print(f"  {r:30s}  {RECEPTORS[r].get('receptor_class', '')}", file=sys.stderr)
        sys.exit(1)

    entry = RECEPTORS[key]
    print("=" * 72)
    print(f"  Receptor: {key}")
    print("=" * 72)
    print(f"  Full name         : {entry.get('full_name', key)}")
    print(f"  Receptor class    : {entry.get('receptor_class', 'see note')}")
    if "superfamily" in entry:
        print(f"  Superfamily       : {entry['superfamily']}")
    if "stoichiometry" in entry:
        print(f"  Stoichiometry     : {entry['stoichiometry']}")
    if "ion_selectivity" in entry:
        print(f"  Ion selectivity   : {entry['ion_selectivity']}")
    if "subunit_families" in entry:
        print()
        print("  Subunit families:")
        for s in entry["subunit_families"]:
            print(f"    • {s}")
    if "typical_composition" in entry:
        print(f"  Typical composition: {entry['typical_composition']}")
    if "rho_subunits" in entry:
        print()
        print(f"  Rho subunits note : {entry['rho_subunits']}")
    if "subtypes" in entry:
        print()
        print("  Subtypes:")
        for st, desc in entry["subtypes"].items():
            print(f"    {st}: {desc}")
    if "signal_transduction" in entry:
        print()
        print("  Signal transduction:")
        for s in entry["signal_transduction"]:
            print(f"    • {s}")
    if "pharmacology" in entry:
        print()
        print("  Pharmacology:")
        for p in entry["pharmacology"]:
            print(f"    • {p}")
    if "locations" in entry:
        print()
        print("  Locations: " + ", ".join(entry["locations"]))
    if "gene_names" in entry:
        print()
        print("  Gene name map (subunit -> HGNC symbol):")
        for sub, gene in entry["gene_names"].items():
            print(f"    {sub:6s} -> {gene}")
    if "key_distinctions" in entry:
        print()
        print("  KEY DISTINCTIONS (common exam/agent errors):")
        for d in entry["key_distinctions"]:
            print(f"    !! {d}")
    print()
    print("=" * 72)
    print("  Verification: entry retrieved from built-in database. [OK]")
    print("=" * 72)


def _lookup_ion_channel(name: str) -> None:
    key = _resolve_key(name, ION_CHANNELS)
    if key is None:
        print(f"ERROR: No ion channel entry for '{name}'.", file=sys.stderr)
        print("Available entries:", file=sys.stderr)
        for c in sorted(ION_CHANNELS):
            print(f"  {c:25s}  {ION_CHANNELS[c].get('stoichiometry', '')}", file=sys.stderr)
        sys.exit(1)

    entry = ION_CHANNELS[key]
    print("=" * 72)
    print(f"  Ion Channel: {key}")
    print("=" * 72)
    print(f"  Full name    : {entry.get('full_name', key)}")
    print(f"  Stoichiometry: {entry.get('stoichiometry', 'see note')}")
    if "subunit_arrangement" in entry:
        print(f"  Subunits     : {entry['subunit_arrangement']}")
    if "rho_homomers" in entry:
        print(f"  Rho homomers : {entry['rho_homomers']}")
    print(f"  Ion          : {entry.get('ion', 'see note')}")
    if "superfamily" in entry:
        print(f"  Superfamily  : {entry['superfamily']}")
    if "subtypes" in entry:
        print()
        print("  Subtypes:")
        for st, desc in entry["subtypes"].items():
            print(f"    {st}: {desc}")
    if "note" in entry:
        print()
        print(f"  NOTE: {entry['note']}")
    print()
    print("=" * 72)
    print("  Verification: entry retrieved from built-in database. [OK]")
    print("=" * 72)


def _lookup_neurotransmitter(name: str) -> None:
    key = _resolve_key(name, NEUROTRANSMITTERS)
    if key is None:
        print(f"ERROR: No neurotransmitter entry for '{name}'.", file=sys.stderr)
        print("Available entries:", file=sys.stderr)
        for nt in sorted(NEUROTRANSMITTERS):
            print(f"  {nt:20s}  {NEUROTRANSMITTERS[nt].get('type', '')}", file=sys.stderr)
        sys.exit(1)

    entry = NEUROTRANSMITTERS[key]
    print("=" * 72)
    print(f"  Neurotransmitter: {key}")
    print("=" * 72)
    print(f"  Full name : {entry.get('full_name', key)}")
    print(f"  Type      : {entry.get('type', 'see note')}")
    print(f"  Synthesis : {entry.get('synthesis', 'see note')}")
    print(f"  Degradation: {entry.get('degradation', 'see note')}")
    if "receptors" in entry:
        print()
        print("  Receptors:")
        for r, desc in entry["receptors"].items():
            print(f"    {r}: {desc}")
    if "function" in entry:
        print()
        print(f"  Function  : {entry['function']}")
    if "key_distinctions" in entry:
        print()
        print("  KEY DISTINCTIONS:")
        for d in entry["key_distinctions"]:
            print(f"    !! {d}")
    print()
    print("=" * 72)
    print("  Verification: entry retrieved from built-in database. [OK]")
    print("=" * 72)


def _lookup_immune_cell(name: str) -> None:
    key = _resolve_key(name, IMMUNE_CELLS)
    if key is None:
        print(f"ERROR: No immune cell entry for '{name}'.", file=sys.stderr)
        print("Available entries:", file=sys.stderr)
        for c in sorted(IMMUNE_CELLS):
            print(f"  {c:20s}  {IMMUNE_CELLS[c].get('lineage', '')}", file=sys.stderr)
        sys.exit(1)

    entry = IMMUNE_CELLS[key]
    print("=" * 72)
    print(f"  Immune Cell: {key}")
    print("=" * 72)
    print(f"  Full name : {entry.get('full_name', key)}")
    print(f"  Lineage   : {entry.get('lineage', 'see note')}")
    print(f"  Origin    : {entry.get('origin_maturation', 'see note')}")
    if "key_markers" in entry:
        print()
        print("  Key markers: " + ", ".join(entry["key_markers"]))
    if "function" in entry:
        print()
        print(f"  Function  : {entry['function']}")
    if "subtypes" in entry:
        print()
        print("  Subtypes:")
        for st, desc in entry["subtypes"].items():
            print(f"    {st}: {desc}")
    if "killing_mechanisms" in entry:
        print()
        print("  Killing mechanisms:")
        for m in entry["killing_mechanisms"]:
            print(f"    • {m}")
    if "activation_mechanism" in entry:
        print()
        print("  Activation mechanisms:")
        for m in entry["activation_mechanism"]:
            print(f"    • {m}")
    if "polarisation" in entry:
        print()
        print("  Polarisation:")
        for p, desc in entry["polarisation"].items():
            print(f"    {p}: {desc}")
    if "key_distinctions" in entry:
        print()
        print("  KEY DISTINCTIONS:")
        for d in entry["key_distinctions"]:
            print(f"    !! {d}")
    print()
    print("=" * 72)
    print("  Verification: entry retrieved from built-in database. [OK]")
    print("=" * 72)


def _lookup_gene_confusion(name: str) -> None:
    key = _resolve_key(name, GENE_CONFUSION)
    if key is None:
        print(f"ERROR: No gene confusion entry for '{name}'.", file=sys.stderr)
        print("Available entries:", file=sys.stderr)
        for g in sorted(GENE_CONFUSION):
            print(f"  {g:12s}  {GENE_CONFUSION[g].get('encodes', '')}", file=sys.stderr)
        sys.exit(1)

    entry = GENE_CONFUSION[key]
    print("=" * 72)
    print(f"  Gene: {key}")
    print("=" * 72)
    print(f"  Encodes  : {entry.get('encodes', 'see note')}")
    print(f"  Protein  : {entry.get('protein', 'see note')}")
    print(f"  Locus    : {entry.get('locus', 'see note')}")
    if "key_facts" in entry:
        print()
        print("  Key facts:")
        for f in entry["key_facts"]:
            print(f"    • {f}")
    if "gene_family" in entry:
        print()
        print("  Gene family: " + ", ".join(entry["gene_family"]))
    if "commonly_confused_with" in entry:
        confused = entry["commonly_confused_with"]
        if isinstance(confused, list):
            confused = ", ".join(confused)
        print()
        print(f"  Commonly confused with: {confused}")
    if "confusion_note" in entry:
        print()
        print(f"  CONFUSION NOTE: {entry['confusion_note']}")
    print()
    print("=" * 72)
    print("  Verification: entry retrieved from built-in database. [OK]")
    print("=" * 72)


def _list_all(query_type: str) -> None:
    """Print a summary table when no specific query term is given."""
    if query_type == "receptor":
        print("=" * 72)
        print("  Receptors in built-in database")
        print("=" * 72)
        for name, entry in sorted(RECEPTORS.items()):
            rc = entry.get("receptor_class", "")
            st = entry.get("stoichiometry", "")
            print(f"  {name:20s}  {rc:40s}  {st}")
        print("=" * 72)
    elif query_type == "ion_channel":
        print("=" * 72)
        print("  Ion channels in built-in database")
        print("=" * 72)
        for name, entry in sorted(ION_CHANNELS.items()):
            st = entry.get("stoichiometry", "")
            ion = entry.get("ion", "")
            print(f"  {name:25s}  {st:30s}  {ion}")
        print("=" * 72)
    elif query_type == "neurotransmitter":
        print("=" * 72)
        print("  Neurotransmitters in built-in database")
        print("=" * 72)
        for name, entry in sorted(NEUROTRANSMITTERS.items()):
            nt_type = entry.get("type", "")
            fn = entry.get("full_name", "")
            print(f"  {name:20s}  {fn:35s}  {nt_type}")
        print("=" * 72)
    elif query_type == "immune_cell":
        print("=" * 72)
        print("  Immune cells in built-in database")
        print("=" * 72)
        for name, entry in sorted(IMMUNE_CELLS.items()):
            lin = entry.get("lineage", "")
            markers = ", ".join(entry.get("key_markers", [])[:3])
            print(f"  {name:20s}  {lin:35s}  markers: {markers}...")
        print("=" * 72)
    elif query_type == "gene_confusion":
        print("=" * 72)
        print("  Gene confusion entries in built-in database")
        print("=" * 72)
        for name, entry in sorted(GENE_CONFUSION.items()):
            enc = entry.get("encodes", "")
            confused = entry.get("commonly_confused_with", "")
            if isinstance(confused, list):
                confused = ", ".join(confused)
            print(f"  {name:10s}  {enc:45s}  confused with: {confused}")
        print("=" * 72)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=dedent(
            """\
            Biology facts lookup tool — a reference handbook for the agent.
            Query the built-in database instead of guessing.
            """
        ),
        epilog=dedent(
            """\
            Examples:
              python biology_facts.py --type receptor --name "GABAA"
              python biology_facts.py --type receptor --name "GABAB"
              python biology_facts.py --type receptor --name "nicotinic"
              python biology_facts.py --type ion_channel --name "NMDA"
              python biology_facts.py --type ion_channel --name "Kv"
              python biology_facts.py --type neurotransmitter --name "GABA"
              python biology_facts.py --type neurotransmitter --name "acetylcholine"
              python biology_facts.py --type immune_cell --name "B cell"
              python biology_facts.py --type immune_cell --name "NK"
              python biology_facts.py --type gene_confusion --name "GABRA1"
              python biology_facts.py --type gene_confusion --name "BRCA1"
              python biology_facts.py --type gene_confusion --name "TP53"
              python biology_facts.py --type receptor          # list all
              python biology_facts.py --type ion_channel       # list all
              python biology_facts.py --type neurotransmitter  # list all
              python biology_facts.py --type immune_cell       # list all
              python biology_facts.py --type gene_confusion    # list all
            """
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--type",
        required=True,
        choices=["receptor", "ion_channel", "neurotransmitter", "immune_cell", "gene_confusion"],
        help="Which fact category to query.",
    )
    p.add_argument(
        "--name",
        type=str,
        default=None,
        help="Name/alias to look up (e.g. 'GABAA', 'B cell', 'GABRA1').",
    )
    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.name is None:
        _list_all(args.type)
        return

    if args.type == "receptor":
        _lookup_receptor(args.name)
    elif args.type == "ion_channel":
        _lookup_ion_channel(args.name)
    elif args.type == "neurotransmitter":
        _lookup_neurotransmitter(args.name)
    elif args.type == "immune_cell":
        _lookup_immune_cell(args.name)
    elif args.type == "gene_confusion":
        _lookup_gene_confusion(args.name)


if __name__ == "__main__":
    main()
