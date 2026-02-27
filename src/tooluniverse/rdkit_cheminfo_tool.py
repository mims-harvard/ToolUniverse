# rdkit_cheminfo_tool.py
"""
RDKit Cheminformatics Tools: Pharmacophore Features and Matched Molecular Pairs

Implements:
1. Pharmacophore feature extraction from SMILES
   - Feature types: HBD, HBA, Aromatic, Hydrophobic, PosIonizable, NegIonizable
   - Optional 3D feature center coordinates from MMFF conformer
2. Matched Molecular Pairs (MMP) analysis
   - Identifies common core and transforming fragments between two compounds
   - Computes property deltas and Tanimoto similarity

No external API calls. Requires RDKit.

References:
- Pharmacophore: Leach et al., Drug Discovery Today (2010)
- MMP: Hussain & Rea, J. Chem. Inf. Model. (2010)
"""

from typing import Dict, Any

from .base_tool import BaseTool
from .tool_registry import register_tool

try:
    from rdkit import Chem, DataStructs
    from rdkit.Chem import Descriptors, rdMolDescriptors, AllChem

    HAS_RDKIT = True
except ImportError:
    HAS_RDKIT = False

try:
    from rdkit.Chem import rdMMPA

    HAS_MMPA = True
except ImportError:
    HAS_MMPA = False

# SMARTS patterns for pharmacophore features.
# Each dict value is a LIST of complete SMARTS strings (not comma-joined),
# because complex patterns (Hydrophobic, PosIonizable, NegIonizable) contain
# internal commas as OR operators that must not be used as separators.
_PHARM_SMARTS: Dict[str, list] = {
    # Three separate SMARTS: N–H donors, O–H donors, S–H donors
    "HBD": ["[#7;!H0;v3,v4&+1]", "[#8;!H0]", "[#16;!H0]"],
    # Four separate SMARTS: tertiary N acceptors, ether/carbonyl O, aromatic O, S acceptors
    "HBA": [
        "[#7;H0;v3,$([N;H0;+0;$(N-a)])]",
        "[#8;H0;+0]",
        "[o;H0]",
        "[#16;H0;v2]",
    ],
    "Aromatic": ["a"],
    # Hydrophobic: split into simple, valid SMARTS to avoid nested-SMARTS parse errors.
    # Aromatic/heteroaromatic + heavy halogens + non-polar S; aliphatic sp3 C (CH3/CH2/CH)
    "Hydrophobic": [
        "[c,s,Br,I,S&H0&v2]",  # aromatic C/S, heavy halogens, thioether S
        "[CX4H3]",  # methyl carbons
        "[CX4H2]",  # methylene carbons
        "[CX4H1]",  # methine carbons
    ],
    # Single recursive SMARTS — must not be split
    "PosIonizable": [
        "[$([NH2;+0;$(N-[!$([OH,OX1])])]),"
        "$([NH;+0;$(N(-[!$([OH,OX1])])-[!$([OH,OX1])])]),"
        "$([N;H0;+0;$(N(-[!$([OH,OX1])])"
        "(-[!$([OH,OX1])])-[!$([OH,OX1])])]),"
        "$([n;H0;+0]),$([NH;+]),$([NH2;+])]"
    ],
    # Single recursive SMARTS — must not be split
    "NegIonizable": [
        "[$([C,S](=[O,S,P])-[O;H1,H0&-1]),$([#7;v5;$(N(-[O;H0&-1])-[OX2;H0])])]"
    ],
}


@register_tool("RDKitCheminfoTool")
class RDKitCheminfoTool(BaseTool):
    """
    RDKit-based cheminformatics tools for pharmacophore and MMP analysis.

    Endpoints:
    - pharmacophore_features: Extract pharmacophore feature centers from SMILES
    - matched_molecular_pair: Find molecular transformation between two SMILES
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "pharmacophore_features")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not HAS_RDKIT:
            return {
                "status": "error",
                "error": "RDKit is required. Install with: pip install rdkit",
            }

        try:
            if self.endpoint == "pharmacophore_features":
                return self._pharmacophore_features(arguments)
            elif self.endpoint == "matched_molecular_pair":
                return self._matched_molecular_pair(arguments)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown endpoint: {self.endpoint}",
                }
        except Exception as e:
            return {
                "status": "error",
                "error": f"RDKit cheminformatics error: {str(e)}",
            }

    def _parse_smiles(self, smiles: str):
        if not smiles or not smiles.strip():
            return None, "smiles is required"
        mol = Chem.MolFromSmiles(smiles.strip())
        if mol is None:
            return None, f"Invalid SMILES: {smiles}"
        return mol, None

    def _get_descriptors(self, mol) -> Dict[str, Any]:
        return {
            "MW": round(Descriptors.ExactMolWt(mol), 2),
            "cLogP": round(Descriptors.MolLogP(mol), 3),
            "HBD": int(rdMolDescriptors.CalcNumHBD(mol)),
            "HBA": int(rdMolDescriptors.CalcNumHBA(mol)),
            "TPSA": round(Descriptors.TPSA(mol), 2),
            "rotatable_bonds": int(rdMolDescriptors.CalcNumRotatableBonds(mol)),
            "heavy_atoms": int(mol.GetNumHeavyAtoms()),
            "rings": int(rdMolDescriptors.CalcNumRings(mol)),
        }

    def _pharmacophore_features(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Extract pharmacophore features from SMILES using SMARTS matching."""
        smiles = arguments.get("smiles", "").strip()
        mol, err = self._parse_smiles(smiles)
        if err:
            return {"status": "error", "error": err}

        include_features = arguments.get("include_features")
        if include_features is None:
            include_features = list(_PHARM_SMARTS.keys())

        features_found: Dict[str, Any] = {}
        feature_counts: Dict[str, int] = {}

        for feature_name in include_features:
            if feature_name not in _PHARM_SMARTS:
                continue

            atom_indices: set = set()

            for smarts in _PHARM_SMARTS[feature_name]:  # already a list
                smarts = smarts.strip()
                if not smarts:
                    continue
                try:
                    pattern = Chem.MolFromSmarts(smarts)
                    if pattern is None:
                        continue
                    for match in mol.GetSubstructMatches(pattern):
                        atom_indices.update(match)
                except Exception:
                    continue

            features_found[feature_name] = {
                "count": len(atom_indices),
                "atom_indices": sorted(list(atom_indices)),
            }
            feature_counts[feature_name] = len(atom_indices)

        # Attempt 3D conformer generation for feature center coordinates
        feature_centers_3d = None
        try:
            mol_h = Chem.AddHs(mol)
            embed_result = AllChem.EmbedMolecule(mol_h, randomSeed=42)
            if embed_result == 0:
                AllChem.MMFFOptimizeMolecule(mol_h)
                conf = mol_h.GetConformer()
                centers = {}
                for fname, fdata in features_found.items():
                    indices = fdata["atom_indices"]
                    if indices:
                        try:
                            positions = [conf.GetAtomPosition(idx) for idx in indices]
                            n = len(positions)
                            center = [
                                round(sum(p.x for p in positions) / n, 3),
                                round(sum(p.y for p in positions) / n, 3),
                                round(sum(p.z for p in positions) / n, 3),
                            ]
                            centers[fname] = center
                        except Exception:
                            pass
                feature_centers_3d = centers if centers else None
        except Exception:
            pass

        n_hbd = feature_counts.get("HBD", 0)
        n_hba = feature_counts.get("HBA", 0)
        n_arom = feature_counts.get("Aromatic", 0)
        n_hydro = feature_counts.get("Hydrophobic", 0)

        return {
            "status": "success",
            "data": {
                "smiles": smiles,
                "pharmacophore_features": features_found,
                "feature_counts": feature_counts,
                "feature_centers_3d": feature_centers_3d,
                "interpretation": {
                    "HBD_count": n_hbd,
                    "HBA_count": n_hba,
                    "aromatic_atom_count": n_arom,
                    "hydrophobic_atom_count": n_hydro,
                    "hbd_hba_ratio": round(n_hbd / n_hba, 2) if n_hba > 0 else None,
                    "3d_available": feature_centers_3d is not None,
                    "note": (
                        "High hydrophobic + low HBA may indicate poor aqueous solubility. "
                        "HBD/HBA ratio influences membrane permeability (Ro5). "
                        + (
                            "3D feature centers computed from MMFF conformer."
                            if feature_centers_3d
                            else "3D conformer generation failed; 2D feature counts provided."
                        )
                    ),
                },
            },
            "metadata": {
                "source": "RDKit local computation",
                "method": "SMARTS-based pharmacophore features",
                "3d_method": "MMFF optimization via AllChem.EmbedMolecule",
                "reference": "Leach et al. (2010); RDKit MolChemicalFeatures",
            },
        }

    def _matched_molecular_pair(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Find MMP transformation between two SMILES compounds."""
        smiles_a = arguments.get("smiles_a", "").strip()
        smiles_b = arguments.get("smiles_b", "").strip()

        mol_a, err = self._parse_smiles(smiles_a)
        if err:
            return {"status": "error", "error": f"smiles_a: {err}"}

        mol_b, err = self._parse_smiles(smiles_b)
        if err:
            return {"status": "error", "error": f"smiles_b: {err}"}

        canonical_a = Chem.MolToSmiles(mol_a)
        canonical_b = Chem.MolToSmiles(mol_b)

        desc_a = self._get_descriptors(mol_a)
        desc_b = self._get_descriptors(mol_b)
        deltas = {k: round(desc_b[k] - desc_a[k], 3) for k in desc_a}

        # Tanimoto similarity (Morgan r=2 fingerprints)
        tanimoto = None
        try:
            fp_a = AllChem.GetMorganFingerprintAsBitVect(mol_a, 2, nBits=2048)
            fp_b = AllChem.GetMorganFingerprintAsBitVect(mol_b, 2, nBits=2048)
            tanimoto = round(float(DataStructs.TanimotoSimilarity(fp_a, fp_b)), 4)
        except Exception:
            pass

        # MMP analysis via rdMMPA fragmentation
        mmp_result: Dict[str, Any] = {}
        if HAS_MMPA:
            try:
                frags_a = rdMMPA.FragmentMol(
                    mol_a, minCuts=1, maxCuts=1, maxCutBonds=100
                )
                frags_b = rdMMPA.FragmentMol(
                    mol_b, minCuts=1, maxCuts=1, maxCutBonds=100
                )

                # rdMMPA.FragmentMol returns (None, combined_mol) tuples where
                # combined_mol contains both sidechain and core as disconnected
                # fragments joined by '.' in the SMILES (both carry [*:1] attachment).
                # Use GetMolFrags to separate them; larger fragment = core.
                from rdkit.Chem import rdmolops

                def _split_frag_pair(frag_pair):
                    """Return (core_smi, sc_smi) or (None, None) on failure."""
                    if len(frag_pair) < 2 or frag_pair[1] is None:
                        return None, None
                    combined = frag_pair[1]
                    parts = rdmolops.GetMolFrags(combined, asMols=True)
                    if len(parts) != 2:
                        return None, None
                    # Larger fragment = core; smaller = sidechain
                    parts_sorted = sorted(parts, key=lambda m: m.GetNumHeavyAtoms())
                    sc_mol, core_mol = parts_sorted[0], parts_sorted[1]
                    return Chem.MolToSmiles(core_mol), Chem.MolToSmiles(sc_mol)

                cores_a: Dict[str, str] = {}
                for frag_pair in frags_a:
                    core_smi, sc_smi = _split_frag_pair(frag_pair)
                    if core_smi:
                        cores_a[core_smi] = sc_smi or ""

                cores_b: Dict[str, str] = {}
                for frag_pair in frags_b:
                    core_smi, sc_smi = _split_frag_pair(frag_pair)
                    if core_smi:
                        cores_b[core_smi] = sc_smi or ""

                common = set(cores_a.keys()) & set(cores_b.keys())
                if common:
                    # Pick largest common core by heavy atom count
                    best_core = max(
                        common,
                        key=lambda s: Chem.MolFromSmiles(s).GetNumHeavyAtoms()
                        if Chem.MolFromSmiles(s)
                        else 0,
                    )
                    sc_a = cores_a.get(best_core, "")
                    sc_b = cores_b.get(best_core, "")
                    mmp_result = {
                        "is_mmp": True,
                        "common_core_smiles": best_core,
                        "side_chain_a": sc_a,
                        "side_chain_b": sc_b,
                        "transformation": f"{sc_a} → {sc_b}",
                        "n_common_cores_found": len(common),
                    }
                else:
                    mmp_result = {
                        "is_mmp": False,
                        "note": (
                            "No common core found with single-cut fragmentation. "
                            "Compounds may differ by multiple structural changes."
                        ),
                    }
            except Exception as e:
                mmp_result = {
                    "is_mmp": None,
                    "error": f"MMP fragmentation failed: {str(e)}",
                }
        else:
            mmp_result = {
                "is_mmp": None,
                "note": "rdMMPA module not available in this RDKit build.",
            }

        if tanimoto is not None:
            if tanimoto >= 0.85:
                sim_label = "High (≥0.85) — likely MMP"
            elif tanimoto >= 0.5:
                sim_label = "Moderate (0.5–0.85)"
            else:
                sim_label = "Low (<0.5) — structurally distinct"
        else:
            sim_label = None

        return {
            "status": "success",
            "data": {
                "smiles_a": canonical_a,
                "smiles_b": canonical_b,
                "tanimoto_similarity": tanimoto,
                "similarity_label": sim_label,
                "mmp_analysis": mmp_result,
                "property_deltas": {
                    "description": "Change in properties (B minus A). Positive = increase in compound B.",
                    "deltas": deltas,
                    "formatted": {
                        "ΔMW": f"{deltas['MW']:+.1f} Da",
                        "ΔcLogP": f"{deltas['cLogP']:+.3f}",
                        "ΔHBD": f"{deltas['HBD']:+d}",
                        "ΔHBA": f"{deltas['HBA']:+d}",
                        "ΔTPSA": f"{deltas['TPSA']:+.1f} Å²",
                    },
                },
                "descriptors": {
                    "compound_a": desc_a,
                    "compound_b": desc_b,
                },
            },
            "metadata": {
                "source": "RDKit local computation",
                "method": "rdMMPA single-cut fragmentation + Morgan r=2 Tanimoto",
                "reference": "Hussain & Rea, J. Chem. Inf. Model. (2010)",
            },
        }
