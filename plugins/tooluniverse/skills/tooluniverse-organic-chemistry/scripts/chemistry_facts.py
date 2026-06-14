"""Reference lookup tool for commonly-tested chemical and physical facts.

This is a LOOKUP TOOL, not a memorization aid. Use it to verify facts
rather than guessing — treat it like querying a reference handbook.

Usage:
    python chemistry_facts.py --type allotropes --element P
    python chemistry_facts.py --type allotropes --element C
    python chemistry_facts.py --type allotropes --element S
    python chemistry_facts.py --type allotropes --element O
    python chemistry_facts.py --type point_group --molecule "water"
    python chemistry_facts.py --type point_group --molecule "ammonia"
    python chemistry_facts.py --type point_group --molecule "benzene"
    python chemistry_facts.py --type common_reagents --reagent "LiAlH4"
    python chemistry_facts.py --type common_reagents --reagent "mCPBA"
    python chemistry_facts.py --type common_reagents --reagent "OsO4"
    python chemistry_facts.py --type allotropes          # list all elements with entries
    python chemistry_facts.py --type point_group         # list all molecules with entries
    python chemistry_facts.py --type common_reagents     # list all reagents
"""

import argparse
import sys
from textwrap import dedent

# ---------------------------------------------------------------------------
# DATABASE: allotropes
# ---------------------------------------------------------------------------
# Key: uppercase element symbol.
# Value: list of dicts describing each allotrope.
#
# For phosphorus the count is 6 distinct colour-named forms. This is a
# common exam trap: students forget scarlet and violet and count only 4.
# ---------------------------------------------------------------------------

ALLOTROPES: dict[str, dict] = {
    "P": {
        "element": "Phosphorus",
        "count": 6,
        "note": (
            "Six colour-named allotropes exist. "
            "A common error is listing only 4 (white/red/violet/black) "
            "and omitting scarlet and diphosphorus."
        ),
        "allotropes": [
            {
                "name": "White phosphorus",
                "formula": "P4",
                "description": (
                    "Tetrahedral P4 molecules. Waxy white solid, highly reactive, "
                    "spontaneously ignites in air (pyrophoric), stored under water."
                ),
                "state_at_STP": "solid",
            },
            {
                "name": "Red phosphorus",
                "formula": "polymeric (Pn)",
                "description": (
                    "Amorphous polymer of linked P4 units. Much less reactive than white. "
                    "Used in match heads."
                ),
                "state_at_STP": "solid",
            },
            {
                "name": "Scarlet phosphorus",
                "formula": "polymeric (Pn)",
                "description": (
                    "Distinct metastable form between red and violet. "
                    "Bright scarlet/orange-red colour. Often omitted in textbooks."
                ),
                "state_at_STP": "solid",
            },
            {
                "name": "Violet phosphorus (Hittorf's phosphorus)",
                "formula": "polymeric (Pn)",
                "description": (
                    "Crystalline monoclinic form. Prepared by slow crystallisation "
                    "from molten lead. Thermodynamically most stable form."
                ),
                "state_at_STP": "solid",
            },
            {
                "name": "Black phosphorus",
                "formula": "layered (Pn)",
                "description": (
                    "Graphite-like layered structure. Semiconductor. "
                    "Produced under high pressure. Most thermodynamically stable at "
                    "ambient conditions after violet."
                ),
                "state_at_STP": "solid",
            },
            {
                "name": "Diphosphorus (violet/gas)",
                "formula": "P2",
                "description": (
                    "Diatomic P2, analogous to N2. Stable only at very high temperatures "
                    "(>1200 °C) or in the gas phase; not isolable as a condensed allotrope "
                    "under normal conditions. Counted as the 6th allotrope in standard references."
                ),
                "state_at_STP": "gas (only at high T)",
            },
        ],
    },
    "C": {
        "element": "Carbon",
        "count": "many (key ones listed below)",
        "note": (
            "Carbon has the richest allotropy of any element. "
            "The most commonly tested are: diamond, graphite, graphene, fullerene (C60), "
            "carbon nanotubes, and amorphous carbon."
        ),
        "allotropes": [
            {
                "name": "Diamond",
                "formula": "C (cubic)",
                "description": (
                    "Each carbon sp3-hybridised, tetrahedral 3D network. "
                    "Hardest natural substance (Mohs 10), electrical insulator, "
                    "excellent thermal conductor."
                ),
                "state_at_STP": "solid",
            },
            {
                "name": "Graphite",
                "formula": "C (hexagonal layers)",
                "description": (
                    "sp2 hexagonal layers held by van der Waals forces. "
                    "Electrical conductor (delocalised pi system), lubricant, "
                    "thermodynamically most stable allotrope at STP."
                ),
                "state_at_STP": "solid",
            },
            {
                "name": "Graphene",
                "formula": "C (single layer)",
                "description": (
                    "Single atomic layer of graphite. sp2 honeycomb lattice. "
                    "Exceptional electrical/thermal conductor, strongest known material per unit weight."
                ),
                "state_at_STP": "solid (2D)",
            },
            {
                "name": "Buckminsterfullerene (C60)",
                "formula": "C60",
                "description": (
                    "Spherical cage of 60 sp2 carbons in pentagons and hexagons. "
                    "First fullerene isolated. Soluble in organic solvents. "
                    "Named after R. Buckminster Fuller."
                ),
                "state_at_STP": "solid",
            },
            {
                "name": "Carbon nanotubes (CNT)",
                "formula": "Cn (tubular)",
                "description": (
                    "Rolled graphene sheets. Single-walled (SWCNT) or multi-walled (MWCNT). "
                    "Metallic or semiconducting depending on chirality."
                ),
                "state_at_STP": "solid",
            },
            {
                "name": "Amorphous carbon",
                "formula": "C (disordered)",
                "description": (
                    "No long-range order. Includes coal, soot, and activated carbon. "
                    "Mixed sp2/sp3 hybridisation."
                ),
                "state_at_STP": "solid",
            },
            {
                "name": "Lonsdaleite (hexagonal diamond)",
                "formula": "C (hexagonal)",
                "description": (
                    "Hexagonal polymorph of diamond found in meteorites. "
                    "sp3 bonding like cubic diamond but different stacking sequence."
                ),
                "state_at_STP": "solid",
            },
        ],
    },
    "S": {
        "element": "Sulfur",
        "count": 3,
        "note": (
            "Three allotropes are commonly tested: rhombic (alpha), monoclinic (beta), "
            "and plastic (amorphous). Rhombic is the stable form at room temperature."
        ),
        "allotropes": [
            {
                "name": "Rhombic sulfur (alpha-sulfur)",
                "formula": "S8 (cyclic)",
                "description": (
                    "Crown-shaped S8 rings packed in orthorhombic crystal. "
                    "Stable below 95.5 °C (transition temperature). "
                    "Most common form found in nature."
                ),
                "state_at_STP": "solid",
            },
            {
                "name": "Monoclinic sulfur (beta-sulfur)",
                "formula": "S8 (cyclic)",
                "description": (
                    "Same S8 rings as rhombic but different packing (monoclinic crystal). "
                    "Stable between 95.5 °C and the melting point (119 °C). "
                    "Converts to rhombic below 95.5 °C."
                ),
                "state_at_STP": "solid (metastable at room temp)",
            },
            {
                "name": "Plastic sulfur (amorphous sulfur)",
                "formula": "Sn (polymeric chains)",
                "description": (
                    "Rubbery, stretchable amorphous form. Produced by pouring molten sulfur "
                    "into cold water, quenching the liquid before S8 rings can crystallise. "
                    "Reverts to rhombic sulfur slowly at room temperature."
                ),
                "state_at_STP": "solid (metastable)",
            },
        ],
    },
    "O": {
        "element": "Oxygen",
        "count": 2,
        "note": (
            "Two allotropes: dioxygen (O2, the common form) and ozone (O3). "
            "Tetraoxygen (O4) and solid oxygen phases exist but are not standard exam topics."
        ),
        "allotropes": [
            {
                "name": "Dioxygen (O2)",
                "formula": "O2",
                "description": (
                    "Diatomic molecule. Paramagnetic (two unpaired electrons in pi* MOs). "
                    "Bond order = 2. The normal allotrope in Earth's atmosphere (~21%)."
                ),
                "state_at_STP": "gas",
            },
            {
                "name": "Ozone (O3)",
                "formula": "O3",
                "description": (
                    "Bent triatomic molecule, bond angle 116.8°. Resonance structure. "
                    "Strong oxidising agent. Absorbs UV-B/C in the stratosphere. "
                    "Toxic at ground level. Less stable than O2."
                ),
                "state_at_STP": "gas",
            },
        ],
    },
}

# ---------------------------------------------------------------------------
# DATABASE: point groups
# ---------------------------------------------------------------------------
# Keys are lowercase molecule names (and common aliases).
# ---------------------------------------------------------------------------

POINT_GROUPS: dict[str, dict] = {
    "water": {
        "formula": "H2O",
        "point_group": "C2v",
        "symmetry_elements": ["E", "C2", "sigma_v (plane of molecule)", "sigma_v' (perpendicular plane)"],
        "geometry": "Bent",
        "bond_angle": "104.5°",
        "note": "The C2 axis bisects the H-O-H angle. Two mirror planes: the molecular plane and one perpendicular to it.",
    },
    "h2o": {
        "formula": "H2O",
        "point_group": "C2v",
        "symmetry_elements": ["E", "C2", "sigma_v", "sigma_v'"],
        "geometry": "Bent",
        "bond_angle": "104.5°",
        "note": "See 'water'.",
    },
    "ammonia": {
        "formula": "NH3",
        "point_group": "C3v",
        "symmetry_elements": ["E", "2C3", "3sigma_v"],
        "geometry": "Trigonal pyramidal",
        "bond_angle": "107.8°",
        "note": "Three vertical mirror planes each containing N and one H. Not D3h because molecule is pyramidal (lone pair).",
    },
    "nh3": {
        "formula": "NH3",
        "point_group": "C3v",
        "symmetry_elements": ["E", "2C3", "3sigma_v"],
        "geometry": "Trigonal pyramidal",
        "bond_angle": "107.8°",
        "note": "See 'ammonia'.",
    },
    "methane": {
        "formula": "CH4",
        "point_group": "Td",
        "symmetry_elements": ["E", "8C3", "3C2", "6S4", "6sigma_d"],
        "geometry": "Tetrahedral",
        "bond_angle": "109.47°",
        "note": "Full tetrahedral symmetry. No inversion centre.",
    },
    "ch4": {
        "formula": "CH4",
        "point_group": "Td",
        "symmetry_elements": ["E", "8C3", "3C2", "6S4", "6sigma_d"],
        "geometry": "Tetrahedral",
        "bond_angle": "109.47°",
        "note": "See 'methane'.",
    },
    "benzene": {
        "formula": "C6H6",
        "point_group": "D6h",
        "symmetry_elements": ["E", "2C6", "2C3", "C2", "3C2'", "3C2''", "i", "2S3", "2S6", "sigma_h", "3sigma_d", "3sigma_v"],
        "geometry": "Planar hexagonal",
        "note": "High symmetry with inversion centre. The sigma_h is the molecular plane.",
    },
    "c6h6": {
        "formula": "C6H6",
        "point_group": "D6h",
        "symmetry_elements": ["E", "2C6", "2C3", "C2", "3C2'", "3C2''", "i", "2S3", "2S6", "sigma_h", "3sigma_d", "3sigma_v"],
        "geometry": "Planar hexagonal",
        "note": "See 'benzene'.",
    },
    "ethylene": {
        "formula": "C2H4",
        "point_group": "D2h",
        "symmetry_elements": ["E", "C2(z)", "C2(y)", "C2(x)", "i", "sigma(xy)", "sigma(xz)", "sigma(yz)"],
        "geometry": "Planar",
        "note": "All atoms in one plane. Inversion centre at midpoint of C=C bond.",
    },
    "ethene": {
        "formula": "C2H4",
        "point_group": "D2h",
        "symmetry_elements": ["E", "C2(z)", "C2(y)", "C2(x)", "i", "sigma(xy)", "sigma(xz)", "sigma(yz)"],
        "geometry": "Planar",
        "note": "See 'ethylene'.",
    },
    "c2h4": {
        "formula": "C2H4",
        "point_group": "D2h",
        "geometry": "Planar",
        "note": "See 'ethylene'.",
    },
    "carbon dioxide": {
        "formula": "CO2",
        "point_group": "D_inf_h",
        "symmetry_elements": ["E", "C_inf", "inf*C2", "i", "S_inf", "inf*sigma_v", "sigma_h"],
        "geometry": "Linear",
        "bond_angle": "180°",
        "note": "Linear molecule with inversion centre. IR-inactive symmetric stretch; IR-active asymmetric stretch and bend.",
    },
    "co2": {
        "formula": "CO2",
        "point_group": "D_inf_h",
        "geometry": "Linear",
        "note": "See 'carbon dioxide'.",
    },
    "hydrogen chloride": {
        "formula": "HCl",
        "point_group": "C_inf_v",
        "symmetry_elements": ["E", "C_inf", "inf*sigma_v"],
        "geometry": "Linear diatomic (heteronuclear)",
        "note": "No inversion centre because the two ends are different. Polar molecule.",
    },
    "hcl": {
        "formula": "HCl",
        "point_group": "C_inf_v",
        "geometry": "Linear diatomic (heteronuclear)",
        "note": "See 'hydrogen chloride'.",
    },
    "hydrogen": {
        "formula": "H2",
        "point_group": "D_inf_h",
        "symmetry_elements": ["E", "C_inf", "inf*C2", "i", "S_inf", "inf*sigma_v"],
        "geometry": "Linear diatomic (homonuclear)",
        "note": "Inversion centre present because both ends are identical.",
    },
    "h2": {
        "formula": "H2",
        "point_group": "D_inf_h",
        "geometry": "Linear diatomic (homonuclear)",
        "note": "See 'hydrogen'.",
    },
    "boron trifluoride": {
        "formula": "BF3",
        "point_group": "D3h",
        "symmetry_elements": ["E", "2C3", "3C2", "sigma_h", "2S3", "3sigma_v"],
        "geometry": "Trigonal planar",
        "bond_angle": "120°",
        "note": "Planar, no lone pair on B (empty p orbital). Not polar overall.",
    },
    "bf3": {
        "formula": "BF3",
        "point_group": "D3h",
        "geometry": "Trigonal planar",
        "note": "See 'boron trifluoride'.",
    },
    "phosphorus pentachloride": {
        "formula": "PCl5",
        "point_group": "D3h",
        "symmetry_elements": ["E", "2C3", "3C2", "sigma_h", "2S3", "3sigma_v"],
        "geometry": "Trigonal bipyramidal",
        "note": "Three equatorial Cl (120° apart) and two axial Cl (180° apart). The equatorial and axial Cl are NOT equivalent.",
    },
    "pcl5": {
        "formula": "PCl5",
        "point_group": "D3h",
        "geometry": "Trigonal bipyramidal",
        "note": "See 'phosphorus pentachloride'.",
    },
    "sulfur hexafluoride": {
        "formula": "SF6",
        "point_group": "Oh",
        "symmetry_elements": ["E", "8C3", "6C2", "6C4", "3C2", "i", "6S4", "8S6", "3sigma_h", "6sigma_d"],
        "geometry": "Octahedral",
        "bond_angle": "90°",
        "note": "Full octahedral symmetry. All S-F bonds equivalent. Non-polar.",
    },
    "sf6": {
        "formula": "SF6",
        "point_group": "Oh",
        "geometry": "Octahedral",
        "note": "See 'sulfur hexafluoride'.",
    },
    "hydrogen peroxide": {
        "formula": "H2O2",
        "point_group": "C2",
        "symmetry_elements": ["E", "C2"],
        "geometry": "Non-planar (skewed)",
        "note": (
            "The O-O bond allows rotation; the two OH groups are skewed relative to each other. "
            "Only a C2 axis, no mirror planes — hence C2 not C2v. Chiral in principle."
        ),
    },
    "h2o2": {
        "formula": "H2O2",
        "point_group": "C2",
        "geometry": "Non-planar (skewed)",
        "note": "See 'hydrogen peroxide'.",
    },
    "cyclohexane": {
        "formula": "C6H12",
        "point_group": "D3d (chair conformation)",
        "symmetry_elements": ["E", "2C3", "3C2", "i", "2S6", "3sigma_d"],
        "geometry": "Chair conformation",
        "note": (
            "Chair cyclohexane has D3d symmetry with an inversion centre. "
            "The boat conformation has C2v symmetry. "
            "The twist-boat has D2 symmetry."
        ),
    },
    "allene": {
        "formula": "C3H4",
        "point_group": "D2d",
        "symmetry_elements": ["E", "2S4", "C2", "2C2'", "2sigma_d"],
        "geometry": "Linear C=C=C with perpendicular CH2 planes",
        "note": (
            "The two CH2 planes are perpendicular to each other. "
            "D2d has an S4 axis but no sigma_h — not D2h. "
            "Allene is a chiral molecule when the two terminal groups differ."
        ),
    },
    "formaldehyde": {
        "formula": "CH2O",
        "point_group": "C2v",
        "symmetry_elements": ["E", "C2", "sigma_v", "sigma_v'"],
        "geometry": "Planar, trigonal",
        "note": "Planar molecule. C2 axis along C=O bond. Both mirror planes contain the C2 axis.",
    },
    "ch2o": {
        "formula": "CH2O",
        "point_group": "C2v",
        "geometry": "Planar, trigonal",
        "note": "See 'formaldehyde'.",
    },
}

# ---------------------------------------------------------------------------
# DATABASE: common reagents
# ---------------------------------------------------------------------------

REAGENTS: dict[str, dict] = {
    "LiAlH4": {
        "full_name": "Lithium aluminium hydride",
        "abbreviations": ["LAH", "LiAlH4"],
        "category": "Reducing agent (strong, non-selective)",
        "primary_function": "Strong, non-selective hydride reducing agent",
        "reduces": [
            "Carboxylic acids → primary alcohols",
            "Esters → two alcohols (primary from the carbonyl carbon)",
            "Amides → amines",
            "Aldehydes → primary alcohols",
            "Ketones → secondary alcohols",
            "Epoxides → alcohols (opens at less hindered C)",
            "Alkyl halides → alkanes (SN2)",
            "Nitriles → primary amines",
            "Nitro groups → amines",
        ],
        "does_NOT_reduce": ["Isolated alkenes/alkynes (no reaction)", "Aromatic rings"],
        "conditions": "Anhydrous ether or THF; quench with water carefully (violent reaction with protic solvents)",
        "mechanism": "Hydride (H-) transfer; SN2-like at electrophilic carbon",
        "key_distinction": "Reduces ALL common carbonyl-containing functional groups including carboxylic acids and esters. Use NaBH4 when selectivity is needed.",
        "safety": "Reacts violently with water and protic solvents. Use dry solvents.",
    },
    "LAH": {
        "full_name": "Lithium aluminium hydride",
        "note": "See 'LiAlH4'.",
        "category": "Reducing agent (strong, non-selective)",
        "primary_function": "Strong hydride reducing agent — see LiAlH4 entry for full details.",
    },
    "NaBH4": {
        "full_name": "Sodium borohydride",
        "abbreviations": ["NaBH4"],
        "category": "Reducing agent (mild, selective)",
        "primary_function": "Mild, selective hydride reducing agent",
        "reduces": [
            "Aldehydes → primary alcohols",
            "Ketones → secondary alcohols",
            "Iminium ions → amines (reductive amination)",
        ],
        "does_NOT_reduce": [
            "Carboxylic acids (no reaction)",
            "Esters (no reaction under normal conditions)",
            "Amides (no reaction)",
            "Isolated alkenes/alkynes",
            "Nitro groups (generally no reaction)",
        ],
        "conditions": "Protic solvents (MeOH, EtOH) or THF/water; room temperature",
        "key_distinction": "Selective for aldehydes/ketones over esters and acids. Use LiAlH4 when you need to reduce esters or acids.",
        "safety": "Mild reagent; slow hydrolysis in water, fast in acid.",
    },
    "mCPBA": {
        "full_name": "meta-Chloroperoxybenzoic acid",
        "abbreviations": ["mCPBA", "m-CPBA", "MCPBA"],
        "category": "Oxidant (peracid)",
        "primary_function": "Epoxidation of alkenes (Shi/Jacobsen-Katsuki precursor context); electrophilic oxygen transfer",
        "reactions": [
            "Alkenes → epoxides (syn addition of oxygen across the double bond)",
            "Sulfides → sulfoxides (then sulfones with excess)",
            "Amines → N-oxides",
            "Baeyer-Villiger oxidation of ketones → esters (with the more substituted group migrating)",
        ],
        "stereochemistry": "Delivers oxygen to the less hindered face; syn addition (epoxide retains alkene geometry).",
        "conditions": "CH2Cl2 solvent, 0 °C to room temperature",
        "key_distinction": "The go-to reagent for simple epoxidation. For asymmetric epoxidation of allylic alcohols use Sharpless (Ti/DIPT/TBHP).",
    },
    "m-CPBA": {
        "note": "See 'mCPBA'.",
        "primary_function": "Epoxidation of alkenes — see mCPBA entry.",
        "category": "Oxidant (peracid)",
    },
    "OsO4": {
        "full_name": "Osmium tetroxide",
        "abbreviations": ["OsO4"],
        "category": "Oxidant (dihydroxylation)",
        "primary_function": "Syn dihydroxylation of alkenes → syn-diols (vicinal diols)",
        "reactions": [
            "Alkene + OsO4 → osmate ester intermediate → syn-1,2-diol (after hydrolysis with NMO or H2O2)",
        ],
        "stereochemistry": (
            "SYN addition — both OH groups added to the SAME face of the alkene. "
            "Gives syn-diol (meso from cis-alkene; racemic mixture from trans-alkene)."
        ),
        "contrast_with": "KMnO4 (cold, dilute) also gives syn-diol but less clean. KMnO4 (hot, concentrated) cleaves the C=C.",
        "conditions": "Catalytic OsO4 with co-oxidant NMO (Upjohn procedure) or stoichiometric",
        "toxicity": "Highly toxic (volatile, osmium vapour damages eyes and lungs). Handle in fume hood.",
        "key_distinction": "Syn-diol from OsO4. Anti-diol from mCPBA epoxidation followed by acid-catalysed opening (trans-diaxial).",
    },
    "KMnO4": {
        "full_name": "Potassium permanganate",
        "abbreviations": ["KMnO4"],
        "category": "Oxidant (versatile)",
        "primary_function": "Oxidation of alkenes; conditions determine product",
        "reactions": [
            "Cold, dilute, basic KMnO4 → syn-1,2-diol (Baeyer test — purple to brown/black precipitate = positive for alkene/aldehyde)",
            "Hot, concentrated KMnO4 → oxidative cleavage of C=C: internal alkenes → two carboxylic acids; terminal alkenes → carboxylic acid + CO2",
            "Primary alcohols → carboxylic acids",
            "Secondary alcohols → ketones",
            "Aldehydes → carboxylic acids",
            "Benzylic/allylic positions → oxidised",
        ],
        "stereochemistry": "Cold dilute: syn diol.",
        "key_distinction": "Temperature/concentration controls product. Cold/dilute = hydroxylation; hot/concentrated = cleavage.",
    },
    "PCC": {
        "full_name": "Pyridinium chlorochromate",
        "abbreviations": ["PCC"],
        "category": "Oxidant (mild, selective)",
        "primary_function": "Oxidises primary alcohols to aldehydes WITHOUT over-oxidation to carboxylic acid; secondary alcohols to ketones",
        "reactions": [
            "Primary alcohol → aldehyde (stops here, unlike CrO3/Jones)",
            "Secondary alcohol → ketone",
        ],
        "does_NOT_oxidise": ["Tertiary alcohols", "Alkenes (no reaction)", "Isolated C-H bonds"],
        "conditions": "CH2Cl2, mild conditions",
        "key_distinction": "PCC stops at aldehyde. Jones reagent (CrO3/H2SO4/acetone) goes all the way to carboxylic acid.",
    },
    "Jones": {
        "full_name": "Jones reagent (CrO3 / H2SO4 / acetone)",
        "abbreviations": ["Jones reagent", "Jones oxidation"],
        "category": "Oxidant (strong)",
        "primary_function": "Oxidises primary alcohols → carboxylic acids; secondary alcohols → ketones",
        "reactions": [
            "Primary alcohol → carboxylic acid",
            "Secondary alcohol → ketone",
            "Aldehydes → carboxylic acids",
        ],
        "key_distinction": "Unlike PCC, Jones over-oxidises primary alcohols to acids.",
    },
    "Swern": {
        "full_name": "Swern oxidation (DMSO / oxalyl chloride / Et3N)",
        "abbreviations": ["Swern oxidation"],
        "category": "Oxidant (mild, Cr-free)",
        "primary_function": "Oxidises primary alcohols → aldehydes; secondary → ketones. Mild, no over-oxidation.",
        "conditions": "DMSO, (COCl)2, then Et3N; −78 °C",
        "key_distinction": "Chromium-free alternative to PCC. Low temperature avoids epimerisation of sensitive substrates.",
    },
    "Grignard": {
        "full_name": "Grignard reagent (RMgX)",
        "abbreviations": ["Grignard", "RMgX", "Grignard reagent"],
        "category": "Nucleophile (strong, basic)",
        "primary_function": "Carbon nucleophile — adds to electrophilic carbons",
        "reactions": [
            "Formaldehyde (HCHO) + RMgX → primary alcohol (after workup)",
            "Aldehyde + RMgX → secondary alcohol",
            "Ketone + RMgX → tertiary alcohol",
            "Ester + RMgX (2 equiv) → tertiary alcohol (both equivalents add)",
            "CO2 + RMgX → carboxylic acid (after workup)",
            "Epoxide + RMgX → alcohol (opens at less hindered C, SN2)",
        ],
        "incompatible_with": [
            "Acidic protons (O-H, N-H, terminal alkyne C-H) — Grignard acts as a base and is destroyed",
            "Carbonyl groups in the same molecule",
        ],
        "conditions": "Anhydrous ether or THF; prepared from R-X + Mg",
        "key_distinction": "Strong base AND nucleophile. Cannot coexist with protic functional groups.",
    },
    "RMgX": {
        "note": "See 'Grignard'.",
        "primary_function": "Carbon nucleophile — see Grignard entry.",
        "category": "Nucleophile (strong, basic)",
    },
    "DIBAL-H": {
        "full_name": "Diisobutylaluminium hydride",
        "abbreviations": ["DIBAL-H", "DIBAL", "DIBAL-H"],
        "category": "Reducing agent (selective)",
        "primary_function": "Selective reduction of esters/nitriles to aldehydes at −78 °C",
        "reactions": [
            "Ester + 1 equiv DIBAL-H (−78 °C) → aldehyde (after workup)",
            "Nitrile + 1 equiv DIBAL-H (−78 °C) → aldehyde (after workup)",
            "Lactone → lactol or diol depending on conditions",
            "Amides → aldehydes",
        ],
        "key_distinction": "Use DIBAL-H when you need to stop at the aldehyde from an ester/nitrile. LiAlH4 would go all the way to alcohol.",
        "conditions": "−78 °C in hexane or toluene for selective aldehyde stop. Warm up or excess → alcohol.",
    },
    "DIBAL": {
        "note": "See 'DIBAL-H'.",
        "primary_function": "Selective reduction to aldehyde — see DIBAL-H entry.",
        "category": "Reducing agent (selective)",
    },
    "TsCl": {
        "full_name": "Tosyl chloride (p-toluenesulfonyl chloride)",
        "abbreviations": ["TsCl", "p-TsCl"],
        "category": "Activating agent (leaving group installation)",
        "primary_function": "Converts alcohols to tosylates (OTs), installing a good leaving group without inverting configuration",
        "reactions": [
            "R-OH + TsCl/pyridine → R-OTs (tosylate) — retention of configuration at alcohol carbon",
            "The tosylate then undergoes SN2 (inversion) or SN1, E2 etc. as appropriate",
        ],
        "key_distinction": "TsCl converts OH (poor leaving group) to OTs (excellent leaving group, comparable to OBs or OTf). Configuration at the carbon bearing OH is RETAINED during tosylation.",
    },
    "TBAF": {
        "full_name": "Tetrabutylammonium fluoride",
        "abbreviations": ["TBAF"],
        "category": "Deprotecting agent / fluoride source",
        "primary_function": "Removes silyl protecting groups (TMS, TBS, TIPS, TES) from alcohols",
        "reactions": [
            "R-OTBS + TBAF → R-OH (deprotection)",
            "Mild fluoride source for other reactions",
        ],
        "key_distinction": "The standard reagent for silyl ether deprotection. Very selective.",
    },
    "NBS": {
        "full_name": "N-Bromosuccinimide",
        "abbreviations": ["NBS"],
        "category": "Radical brominator / electrophilic bromine source",
        "primary_function": "Allylic and benzylic bromination (radical); electrophilic bromine equivalent for other reactions",
        "reactions": [
            "Allylic C-H + NBS / hv (or AIBN) → allylic bromide (radical mechanism, Wohl-Ziegler)",
            "Benzylic C-H + NBS / hv → benzylic bromide",
            "Alkenes + NBS / H2O → bromohydrin (electrophilic addition)",
            "Alkynes + NBS → vinyl bromide",
        ],
        "key_distinction": "NBS delivers Br• (radical) under light/AIBN. Under ionic conditions acts as electrophilic Br+ equivalent.",
    },
    "AIBN": {
        "full_name": "Azobisisobutyronitrile",
        "abbreviations": ["AIBN"],
        "category": "Radical initiator",
        "primary_function": "Generates carbon radicals on heating (70-80 °C) to initiate radical chain reactions",
        "reactions": [
            "AIBN + heat → 2 isobutyronitrile radicals + N2 (gas, thermodynamic driving force)",
            "Used with NBS for allylic bromination",
            "Used with Bu3SnH for radical dehalogenation (Barton-McCombie etc.)",
        ],
        "key_distinction": "Radical initiator — not itself a reagent in the transformation. N2 gas is released as thermodynamic driving force.",
    },
    "BH3": {
        "full_name": "Borane (BH3, often as BH3·THF or BH3·SMe2)",
        "abbreviations": ["BH3", "BH3·THF", "9-BBN"],
        "category": "Reducing agent / hydroboration reagent",
        "primary_function": "Hydroboration of alkenes (anti-Markovnikov addition of B-H across C=C)",
        "reactions": [
            "Alkene + BH3 → alkylborane (syn addition, anti-Markovnikov: B on less substituted C)",
            "Alkylborane + H2O2/NaOH → alcohol (oxidation; net: anti-Markovnikov syn-hydration)",
            "Reduces carboxylic acids (faster than NaBH4, but not LiAlH4-like broad scope)",
        ],
        "stereochemistry": "SYN addition: H and B add to the same face. Boron goes to less hindered carbon.",
        "key_distinction": "Hydroboration-oxidation gives anti-Markovnikov alcohol with syn stereochemistry. Contrast: acid-catalysed hydration gives Markovnikov alcohol.",
    },
    "DMDO": {
        "full_name": "Dimethyldioxirane",
        "abbreviations": ["DMDO"],
        "category": "Oxidant (mild epoxidation)",
        "primary_function": "Mild epoxidation of alkenes, including electron-poor alkenes where mCPBA fails",
        "reactions": [
            "Alkene + DMDO → epoxide (syn addition, similar to mCPBA but more reactive)",
        ],
        "key_distinction": "Epoxidises electron-poor alkenes (e.g. enones) that resist mCPBA. Generated in situ from Oxone + acetone.",
    },
    "PDC": {
        "full_name": "Pyridinium dichromate",
        "abbreviations": ["PDC"],
        "category": "Oxidant",
        "primary_function": "Similar to PCC but milder and compatible with some acid-sensitive groups",
        "reactions": [
            "Primary alcohol → aldehyde (in CH2Cl2) or carboxylic acid (in DMF)",
            "Secondary alcohol → ketone",
        ],
        "key_distinction": "Solvent controls selectivity: CH2Cl2 → aldehyde; DMF → acid.",
    },
    "DDQ": {
        "full_name": "2,3-Dichloro-5,6-dicyano-1,4-benzoquinone",
        "abbreviations": ["DDQ"],
        "category": "Oxidant (mild, deprotecting agent)",
        "primary_function": "Deprotection of PMB ethers and esters; allylic/benzylic oxidation; aromatisation",
        "reactions": [
            "PMB ether + DDQ → free alcohol (removes p-methoxybenzyl protecting group)",
            "Oxidative aromatisation of dihydropyridines, dihydro-aromatics",
        ],
        "key_distinction": "Standard reagent for PMB deprotection. Very selective over TBS and Bn groups.",
    },
    "DMAP": {
        "full_name": "4-Dimethylaminopyridine",
        "abbreviations": ["DMAP"],
        "category": "Nucleophilic catalyst (acylation catalyst)",
        "primary_function": "Acylation catalyst — dramatically accelerates esterification, acetylation, Boc protection, etc.",
        "reactions": [
            "Alcohol + Ac2O (catalytic DMAP) → ester (rate 10^4 faster than pyridine alone)",
            "Hindered alcohols that resist normal acylation",
        ],
        "key_distinction": "DMAP is a CATALYST. It does not change the stoichiometry — the acylating agent (Ac2O, acyl chloride) is still required.",
    },
    "EDC": {
        "full_name": "1-Ethyl-3-(3-dimethylaminopropyl)carbodiimide",
        "abbreviations": ["EDC", "EDCI", "EDC·HCl"],
        "category": "Coupling reagent",
        "primary_function": "Activates carboxylic acids for amide bond formation (peptide coupling) without racemisation",
        "reactions": [
            "Carboxylic acid + amine + EDC → amide (water-soluble urea byproduct)",
            "Often used with HOBt or sulfo-NHS to suppress racemisation",
        ],
        "key_distinction": "Water-soluble carbodiimide — byproduct is water-soluble and easily removed. Compare DCC (insoluble urea byproduct).",
    },
    "DCC": {
        "full_name": "Dicyclohexylcarbodiimide",
        "abbreviations": ["DCC"],
        "category": "Coupling reagent",
        "primary_function": "Activates carboxylic acids for amide/ester bond formation",
        "reactions": [
            "Carboxylic acid + amine + DCC → amide + DCU (dicyclohexylurea precipitate)",
        ],
        "key_distinction": "DCU byproduct is insoluble — filtered off. Racemisation risk; use with HOBt for peptides.",
    },
    "Pd/C": {
        "full_name": "Palladium on carbon",
        "abbreviations": ["Pd/C", "Pd-C"],
        "category": "Hydrogenation catalyst (heterogeneous)",
        "primary_function": "Catalytic hydrogenation of alkenes and alkynes (H2 atmosphere); hydrogenolysis of Cbz/Bn groups",
        "reactions": [
            "Alkene + H2 / Pd-C → alkane (syn addition of H2)",
            "Alkyne + H2 / Pd-C → alkane (full reduction)",
            "Benzyl ether (OBn) + H2 / Pd-C → free alcohol (hydrogenolysis)",
            "Cbz (Z) amine protection + H2 / Pd-C → free amine",
            "Nitro group → amine (with H2 / Pd-C or transfer hydrogenation)",
        ],
        "stereochemistry": "Syn addition of H2 to alkene face.",
        "key_distinction": "Full reduction to alkane. Use Lindlar's catalyst (Pd/CaCO3/quinoline) to stop at cis-alkene from alkyne.",
    },
    "Lindlar": {
        "full_name": "Lindlar's catalyst (Pd/CaCO3 + quinoline/lead acetate)",
        "abbreviations": ["Lindlar", "Lindlar catalyst"],
        "category": "Hydrogenation catalyst (semi-hydrogenation)",
        "primary_function": "Partial hydrogenation of alkynes → cis (Z) alkenes",
        "reactions": [
            "Internal alkyne + H2 / Lindlar → cis-alkene (Z-alkene)",
        ],
        "stereochemistry": "Syn addition → cis alkene.",
        "key_distinction": "Stops at alkene (poisoned catalyst). Birch reduction or Na/NH3 gives trans (E) alkene from alkyne.",
    },
    "Na/NH3": {
        "full_name": "Sodium in liquid ammonia (Birch-type, dissolving metal)",
        "abbreviations": ["Na/NH3", "Li/NH3"],
        "category": "Dissolving metal reduction",
        "primary_function": "Partial reduction of alkynes → trans (E) alkenes; Birch reduction of aromatic rings",
        "reactions": [
            "Internal alkyne + Na/NH3 → trans-alkene (E-alkene) — via vinyl radical/carbanion",
            "Benzene ring + Na/NH3 + t-BuOH → 1,4-cyclohexadiene (Birch: substituents affect position of double bonds)",
        ],
        "key_distinction": "Gives TRANS alkene from alkyne (opposite of Lindlar). Birch reduction: electron-donating groups leave the double bond adjacent; electron-withdrawing groups leave double bond on the substituted ring position.",
    },
}

# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------


def _lookup_allotropes(element: str) -> None:
    key = element.upper()
    if key not in ALLOTROPES:
        available = ", ".join(sorted(ALLOTROPES.keys()))
        print(f"ERROR: No allotrope data for element '{element}'.", file=sys.stderr)
        print(f"Available elements: {available}", file=sys.stderr)
        sys.exit(1)

    entry = ALLOTROPES[key]
    print("=" * 64)
    print(f"  Allotropes of {entry['element']} ({key})")
    print("=" * 64)
    print(f"  Count : {entry['count']}")
    print(f"  Note  : {entry['note']}")
    print()
    for i, a in enumerate(entry["allotropes"], 1):
        print(f"  [{i}] {a['name']}")
        print(f"       Formula     : {a['formula']}")
        print(f"       State at STP: {a['state_at_STP']}")
        print(f"       Description : {a['description']}")
        print()
    print("=" * 64)
    print(f"  Verification: {len(entry['allotropes'])} allotropes listed above.")
    print("=" * 64)


def _lookup_point_group(molecule: str) -> None:
    key = molecule.lower().strip()
    if key not in POINT_GROUPS:
        available = sorted({k for k in POINT_GROUPS if not POINT_GROUPS[k].get("note", "").startswith("See")})
        print(f"ERROR: No point group data for '{molecule}'.", file=sys.stderr)
        print("Canonical names available:", file=sys.stderr)
        for m in available:
            pg = POINT_GROUPS[m]["point_group"]
            print(f"  {m:30s}  {pg}", file=sys.stderr)
        sys.exit(1)

    entry = POINT_GROUPS[key]
    print("=" * 64)
    print(f"  Point Group: {molecule}")
    print("=" * 64)
    print(f"  Formula     : {entry.get('formula', 'see note')}")
    print(f"  Point group : {entry['point_group']}")
    if "geometry" in entry:
        print(f"  Geometry    : {entry['geometry']}")
    if "bond_angle" in entry:
        print(f"  Bond angle  : {entry['bond_angle']}")
    if "symmetry_elements" in entry:
        elements_str = ", ".join(entry["symmetry_elements"])
        print(f"  Sym. elements: {elements_str}")
    if "note" in entry:
        print()
        print(f"  Note: {entry['note']}")
    print("=" * 64)
    print("  Verification: point group retrieved from built-in database. ✓")
    print("=" * 64)


def _lookup_reagent(reagent: str) -> None:
    # Try exact match first, then case-insensitive
    key = reagent
    if key not in REAGENTS:
        for k in REAGENTS:
            if k.lower() == reagent.lower():
                key = k
                break
        else:
            available = sorted(k for k in REAGENTS if not REAGENTS[k].get("note", "").startswith("See"))
            print(f"ERROR: No entry for reagent '{reagent}'.", file=sys.stderr)
            print("Available reagents:", file=sys.stderr)
            for r in available:
                cat = REAGENTS[r].get("category", "")
                print(f"  {r:20s}  {cat}", file=sys.stderr)
            sys.exit(1)

    entry = REAGENTS[key]
    print("=" * 64)
    print(f"  Reagent: {key}")
    print("=" * 64)
    if "full_name" in entry:
        print(f"  Full name : {entry['full_name']}")
    if "abbreviations" in entry:
        print(f"  Aliases   : {', '.join(entry['abbreviations'])}")
    print(f"  Category  : {entry.get('category', 'see note')}")
    print(f"  Function  : {entry.get('primary_function', 'see note')}")

    if "reduces" in entry:
        print()
        print("  Reduces:")
        for r in entry["reduces"]:
            print(f"    • {r}")
    if "does_NOT_reduce" in entry:
        print()
        print("  Does NOT reduce:")
        for r in entry["does_NOT_reduce"]:
            print(f"    ✗ {r}")
    if "reactions" in entry:
        print()
        print("  Key reactions:")
        for r in entry["reactions"]:
            print(f"    • {r}")
    if "does_NOT_oxidise" in entry:
        print()
        print("  Does NOT oxidise:")
        for r in entry["does_NOT_oxidise"]:
            print(f"    ✗ {r}")
    if "stereochemistry" in entry:
        print()
        print(f"  Stereochemistry: {entry['stereochemistry']}")
    if "conditions" in entry:
        print()
        print(f"  Conditions: {entry['conditions']}")
    if "contrast_with" in entry:
        print()
        print(f"  Contrast with: {entry['contrast_with']}")
    if "incompatible_with" in entry:
        print()
        print("  Incompatible with:")
        for r in entry["incompatible_with"]:
            print(f"    ✗ {r}")
    if "key_distinction" in entry:
        print()
        print(f"  KEY DISTINCTION: {entry['key_distinction']}")
    if "safety" in entry:
        print()
        print(f"  Safety: {entry['safety']}")
    if "note" in entry:
        print()
        print(f"  Note: {entry['note']}")
    print()
    print("=" * 64)
    print("  Verification: entry retrieved from built-in database. ✓")
    print("=" * 64)


def _list_all(query_type: str) -> None:
    """Print a summary table when no specific query term is given."""
    if query_type == "allotropes":
        print("=" * 64)
        print("  Elements with allotrope data")
        print("=" * 64)
        for sym, entry in sorted(ALLOTROPES.items()):
            names = [a["name"] for a in entry["allotropes"]]
            print(f"  {sym:4s}  ({entry['element']})  count={entry['count']}")
            for n in names:
                print(f"        • {n}")
            print()
        print("=" * 64)
    elif query_type == "point_group":
        print("=" * 64)
        print("  Molecules with point group data")
        print("=" * 64)
        canonical = {k: v for k, v in POINT_GROUPS.items() if not v.get("note", "").startswith("See")}
        for mol, entry in sorted(canonical.items()):
            pg = entry["point_group"]
            geo = entry.get("geometry", "")
            print(f"  {mol:30s}  {pg:12s}  {geo}")
        print("=" * 64)
    elif query_type == "common_reagents":
        print("=" * 64)
        print("  Reagents in built-in database")
        print("=" * 64)
        canonical = {k: v for k, v in REAGENTS.items() if not v.get("note", "").startswith("See")}
        for name, entry in sorted(canonical.items()):
            cat = entry.get("category", "")
            fn = entry.get("primary_function", "")
            short_fn = fn[:55] + "…" if len(fn) > 55 else fn
            print(f"  {name:15s}  {cat:35s}  {short_fn}")
        print("=" * 64)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=dedent(
            """\
            Chemistry facts lookup tool — a reference handbook for the agent.
            Query the built-in database instead of guessing.
            """
        ),
        epilog=dedent(
            """\
            Examples:
              python chemistry_facts.py --type allotropes --element P
              python chemistry_facts.py --type allotropes --element C
              python chemistry_facts.py --type point_group --molecule "water"
              python chemistry_facts.py --type point_group --molecule "benzene"
              python chemistry_facts.py --type common_reagents --reagent "LiAlH4"
              python chemistry_facts.py --type common_reagents --reagent "mCPBA"
              python chemistry_facts.py --type allotropes          # list all
              python chemistry_facts.py --type point_group         # list all
              python chemistry_facts.py --type common_reagents     # list all
            """
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--type",
        required=True,
        choices=["allotropes", "point_group", "common_reagents"],
        help="Which fact category to query.",
    )
    p.add_argument(
        "--element",
        type=str,
        default=None,
        help="Element symbol for --type allotropes (e.g. P, C, S, O).",
    )
    p.add_argument(
        "--molecule",
        type=str,
        default=None,
        help="Molecule name for --type point_group (e.g. 'water', 'benzene').",
    )
    p.add_argument(
        "--reagent",
        type=str,
        default=None,
        help="Reagent name/abbreviation for --type common_reagents (e.g. 'LiAlH4', 'mCPBA').",
    )
    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.type == "allotropes":
        if args.element is None:
            _list_all("allotropes")
        else:
            _lookup_allotropes(args.element)

    elif args.type == "point_group":
        if args.molecule is None:
            _list_all("point_group")
        else:
            _lookup_point_group(args.molecule)

    elif args.type == "common_reagents":
        if args.reagent is None:
            _list_all("common_reagents")
        else:
            _lookup_reagent(args.reagent)


if __name__ == "__main__":
    main()
