# drug_properties_tool.py
"""
Drug Property Filters and Drug-likeness Assessment Tool

Implements standard computational drug-likeness filters:
- Lipinski's Rule of Five (Ro5): MW≤500, cLogP≤5, HBD≤5, HBA≤10
- Veber filter: RotBonds≤10, TPSA≤140
- QED (Quantitative Estimate of Drug-likeness): rdkit.Chem.QED
- PAINS (Pan-Assay Interference Compounds): rdkit.Chem.FilterCatalog
- Pfizer 3/75 rule: cLogP≤3, TPSA≥75
- Egan filter, Ghose filter

No external API calls. Requires RDKit.

References:
- Lipinski et al., Adv. Drug Deliv. Rev. (1997)
- Veber et al., J. Med. Chem. (2002)
- Bickerton et al., Nature Chemistry (2012) [QED]
- Baell & Holloway, J. Med. Chem. (2010) [PAINS]
"""

from typing import Dict, Any

from .base_tool import BaseTool
from .tool_registry import register_tool

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, rdMolDescriptors, QED as RDKitQED
    from rdkit.Chem.FilterCatalog import FilterCatalog, FilterCatalogParams

    HAS_RDKIT = True
except Exception:
    HAS_RDKIT = False


@register_tool("DrugPropertiesTool")
class DrugPropertiesTool(BaseTool):
    """
    Drug-likeness property filters and assessments using RDKit.

    Endpoints:
    - lipinski_filter: Lipinski Ro5 + Veber + Pfizer 3/75 + Egan + Ghose
    - calculate_qed: QED score + full descriptor profile
    - pains_filter: PAINS + Brenk + NIH substructure filters
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "lipinski_filter")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not HAS_RDKIT:
            return {
                "status": "error",
                "error": "RDKit is required for drug property calculations. Install with: pip install rdkit",
            }

        try:
            if self.endpoint == "lipinski_filter":
                return self._lipinski_filter(arguments)
            elif self.endpoint == "calculate_qed":
                return self._calculate_qed(arguments)
            elif self.endpoint == "pains_filter":
                return self._pains_filter(arguments)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown endpoint: {self.endpoint}",
                }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Drug property calculation error: {str(e)}",
            }

    def _parse_smiles(self, arguments: Dict[str, Any]):
        smiles = arguments.get("smiles", "").strip()
        if not smiles:
            return None, {
                "status": "error",
                "error": "smiles parameter is required (SMILES string of the molecule)",
            }
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None, {
                "status": "error",
                "error": f"Invalid SMILES string: {smiles}",
            }
        return mol, None

    def _lipinski_filter(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Check Lipinski Ro5, Veber, Pfizer 3/75, Egan, and Ghose filters."""
        mol, err = self._parse_smiles(arguments)
        if err:
            return err

        # Calculate descriptors
        mw = Descriptors.ExactMolWt(mol)
        logp = Descriptors.MolLogP(mol)
        hbd = rdMolDescriptors.CalcNumHBD(mol)
        hba = rdMolDescriptors.CalcNumHBA(mol)
        rotb = rdMolDescriptors.CalcNumRotatableBonds(mol)
        tpsa = Descriptors.TPSA(mol)
        arom_rings = rdMolDescriptors.CalcNumAromaticRings(mol)
        heavy_atoms = mol.GetNumHeavyAtoms()
        mr = Descriptors.MolMR(mol)  # Molar refractivity
        csp3 = rdMolDescriptors.CalcFractionCSP3(mol)

        # Lipinski Ro5 (Lipinski 1997): allow 1 violation
        ro5_violations = sum([mw > 500, logp > 5, hbd > 5, hba > 10])
        lipinski_pass = ro5_violations <= 1

        # Veber (2002): oral bioavailability
        veber_pass = rotb <= 10 and tpsa <= 140

        # Pfizer 3/75 rule (reduces promiscuity / CNS penetration risk)
        pfizer_pass = logp <= 3 and tpsa >= 75

        # Egan filter (Egan 2000): bioavailability
        egan_pass = logp <= 5.88 and tpsa <= 131.6

        # Ghose filter (1999): oral drug-like
        ghose_pass = (
            -0.4 <= logp <= 5.6
            and 160 <= mw <= 480
            and 40 <= mr <= 130
            and 20 <= heavy_atoms <= 70
        )

        # Beyond Ro5 territory (macrocycles / PROTACs)
        beyond_ro5 = ro5_violations > 1 and mw <= 1000

        if lipinski_pass and veber_pass:
            overall = "drug-like"
        elif lipinski_pass:
            overall = "borderline (Ro5 pass, Veber fail)"
        elif beyond_ro5:
            overall = "beyond-Ro5 (macrocycle/PROTAC territory)"
        else:
            overall = "non-drug-like"

        return {
            "status": "success",
            "data": {
                "smiles": arguments.get("smiles", ""),
                "descriptors": {
                    "molecular_weight_Da": round(mw, 2),
                    "cLogP": round(logp, 3),
                    "HBD": hbd,
                    "HBA": hba,
                    "rotatable_bonds": rotb,
                    "TPSA_A2": round(tpsa, 2),
                    "aromatic_rings": arom_rings,
                    "heavy_atoms": heavy_atoms,
                    "molar_refractivity": round(mr, 2),
                    "Csp3_fraction": round(csp3, 3),
                },
                "filters": {
                    "lipinski_ro5": {
                        "pass": bool(lipinski_pass),
                        "violations": ro5_violations,
                        "rule": "MW≤500, cLogP≤5, HBD≤5, HBA≤10 (max 1 violation)",
                    },
                    "veber": {
                        "pass": bool(veber_pass),
                        "rule": "RotBonds≤10, TPSA≤140 Å²",
                    },
                    "pfizer_3_75": {
                        "pass": bool(pfizer_pass),
                        "rule": "cLogP≤3, TPSA≥75 Å² (reduces promiscuity/CNS risk)",
                    },
                    "egan": {
                        "pass": bool(egan_pass),
                        "rule": "cLogP≤5.88, TPSA≤131.6 Å² (Egan et al. 2000)",
                    },
                    "ghose": {
                        "pass": bool(ghose_pass),
                        "rule": "-0.4≤cLogP≤5.6, 160≤MW≤480, 40≤MR≤130, 20≤Atoms≤70",
                    },
                    "beyond_ro5_territory": {
                        "applicable": bool(beyond_ro5),
                        "note": "Fails Lipinski but MW≤1000 — may be viable as macrocycle or PROTAC",
                    },
                },
                "overall_drug_likeness": overall,
            },
            "metadata": {
                "source": "RDKit local computation",
                "filters_applied": "Lipinski (1997), Veber (2002), Pfizer 3/75, Egan (2000), Ghose (1999)",
            },
        }

    def _calculate_qed(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate QED (Quantitative Estimate of Drug-likeness) score."""
        mol, err = self._parse_smiles(arguments)
        if err:
            return err

        mw = Descriptors.ExactMolWt(mol)
        logp = Descriptors.MolLogP(mol)
        hbd = rdMolDescriptors.CalcNumHBD(mol)
        hba = rdMolDescriptors.CalcNumHBA(mol)
        rotb = rdMolDescriptors.CalcNumRotatableBonds(mol)
        tpsa = Descriptors.TPSA(mol)
        arom_rings = rdMolDescriptors.CalcNumAromaticRings(mol)

        qed_score = RDKitQED.qed(mol)
        qed_props = RDKitQED.properties(mol)

        if qed_score >= 0.67:
            qed_category = "High (drug-like)"
        elif qed_score >= 0.34:
            qed_category = "Medium (borderline)"
        else:
            qed_category = "Low (non-drug-like)"

        return {
            "status": "success",
            "data": {
                "smiles": arguments.get("smiles", ""),
                "qed_score": round(qed_score, 4),
                "qed_category": qed_category,
                "qed_components": {
                    "MW": round(qed_props.MW, 2),
                    "ALOGP": round(qed_props.ALOGP, 3),
                    "HBA": qed_props.HBA,
                    "HBD": qed_props.HBD,
                    "PSA": round(qed_props.PSA, 2),
                    "ROTB": qed_props.ROTB,
                    "AROM": qed_props.AROM,
                    "ALERTS": qed_props.ALERTS,
                },
                "additional_descriptors": {
                    "molecular_weight_Da": round(mw, 2),
                    "cLogP": round(logp, 3),
                    "HBD": hbd,
                    "HBA": hba,
                    "rotatable_bonds": rotb,
                    "TPSA_A2": round(tpsa, 2),
                    "aromatic_rings": arom_rings,
                },
                "interpretation": (
                    "QED ranges from 0 (least drug-like) to 1 (most drug-like). "
                    "Median approved drugs: ~0.49. Optimized leads typically >0.5. "
                    "ALERTS = number of structural alerts (Brenk-like). "
                    "Based on Bickerton et al., Nature Chemistry (2012)."
                ),
            },
            "metadata": {
                "source": "RDKit local computation",
                "reference": "Bickerton et al., Nature Chemistry, 2012",
            },
        }

    def _pains_filter(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Check for PAINS, Brenk, and NIH undesirable substructures."""
        mol, err = self._parse_smiles(arguments)
        if err:
            return err

        # PAINS filter (Baell & Holloway 2010)
        params = FilterCatalogParams()
        params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS)
        catalog = FilterCatalog(params)
        pains_matches = []
        for entry in catalog.GetMatches(mol):
            pains_matches.append(
                {
                    "name": entry.GetDescription(),
                    "family": "PAINS",
                }
            )

        # Brenk filter (undesirable reactive/toxic substructures)
        brenk_params = FilterCatalogParams()
        brenk_params.AddCatalog(FilterCatalogParams.FilterCatalogs.BRENK)
        brenk_catalog = FilterCatalog(brenk_params)
        brenk_matches = [
            entry.GetDescription() for entry in brenk_catalog.GetMatches(mol)
        ]

        # NIH filter
        nih_params = FilterCatalogParams()
        nih_params.AddCatalog(FilterCatalogParams.FilterCatalogs.NIH)
        nih_catalog = FilterCatalog(nih_params)
        nih_matches = [entry.GetDescription() for entry in nih_catalog.GetMatches(mol)]

        is_clean = len(pains_matches) == 0 and len(brenk_matches) == 0

        if is_clean:
            recommendation = "Clean — no PAINS or Brenk alerts. Suitable for screening."
        else:
            parts = []
            if pains_matches:
                parts.append(f"{len(pains_matches)} PAINS alert(s)")
            if brenk_matches:
                parts.append(f"{len(brenk_matches)} Brenk alert(s)")
            recommendation = (
                f"CAUTION: {', '.join(parts)}. May cause assay interference or reactivity. "
                "Consider structural optimization."
            )

        return {
            "status": "success",
            "data": {
                "smiles": arguments.get("smiles", ""),
                "is_clean": is_clean,
                "pains": {
                    "pass": len(pains_matches) == 0,
                    "matches": pains_matches,
                    "count": len(pains_matches),
                },
                "brenk": {
                    "pass": len(brenk_matches) == 0,
                    "matches": brenk_matches[:10],
                    "count": len(brenk_matches),
                },
                "nih": {
                    "pass": len(nih_matches) == 0,
                    "matches": nih_matches[:10],
                    "count": len(nih_matches),
                },
                "recommendation": recommendation,
            },
            "metadata": {
                "source": "RDKit local computation",
                "filters": "PAINS (Baell & Holloway 2010), Brenk (2008), NIH",
            },
        }
