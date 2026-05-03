"""
SwissADME Tool

Predicts ADMET properties, drug-likeness, and medicinal chemistry friendliness
of small molecules from SMILES input using SwissADME.

SwissADME does NOT have a formal REST/JSON API. This tool:
1. POSTs SMILES to the web form at index.php
2. Extracts the results directory path from the response HTML
3. Fetches the CSV result file from that directory
4. Parses the CSV into structured property data

The SMILES input format is "SMILES name" per line (name is optional).
When no name is given, SwissADME assigns "Molecule 1".

49 properties are computed across 6 categories:
- Physicochemical: MW, heavy atoms, rotatable bonds, H-bond donors/acceptors, TPSA, etc.
- Lipophilicity: iLOGP, XLOGP3, WLOGP, MLOGP, Silicos-IT, Consensus
- Water Solubility: ESOL, Ali, Silicos-IT (log S, mg/ml, mol/l, class)
- Pharmacokinetics: GI absorption, BBB permeant, Pgp substrate, CYP inhibitors, skin permeation
- Drug-likeness: Lipinski, Ghose, Veber, Egan, Muegge violations, Bioavailability Score
- Medicinal Chemistry: PAINS alerts, Brenk alerts, Leadlikeness, Synthetic Accessibility

Base URL: https://www.swissadme.ch/
No authentication required.

Reference: Daina A, Michielin O, Zoete V. SwissADME: a free web tool to evaluate
pharmacokinetics, drug-likeness and medicinal chemistry friendliness of small molecules.
Scientific Reports, 2017, 7:42717. (PMID: 28256516)
"""

import csv
import io
import re
import requests
from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool


SWISSADME_BASE_URL = "https://www.swissadme.ch"

# Map CSV header names to structured property keys
CSV_FIELD_MAP = {
    "Molecule": "molecule_name",
    "Canonical SMILES": "canonical_smiles",
    "Formula": "formula",
    "MW": "molecular_weight",
    "#Heavy atoms": "num_heavy_atoms",
    "#Aromatic heavy atoms": "num_aromatic_heavy_atoms",
    "Fraction Csp3": "fraction_csp3",
    "#Rotatable bonds": "num_rotatable_bonds",
    "#H-bond acceptors": "num_hbond_acceptors",
    "#H-bond donors": "num_hbond_donors",
    "MR": "molar_refractivity",
    "TPSA": "tpsa",
    "iLOGP": "ilogp",
    "XLOGP3": "xlogp3",
    "WLOGP": "wlogp",
    "MLOGP": "mlogp",
    "Silicos-IT Log P": "silicosit_logp",
    "Consensus Log P": "consensus_logp",
    "ESOL Log S": "esol_logs",
    "ESOL Solubility (mg/ml)": "esol_solubility_mg_ml",
    "ESOL Solubility (mol/l)": "esol_solubility_mol_l",
    "ESOL Class": "esol_class",
    "Ali Log S": "ali_logs",
    "Ali Solubility (mg/ml)": "ali_solubility_mg_ml",
    "Ali Solubility (mol/l)": "ali_solubility_mol_l",
    "Ali Class": "ali_class",
    "Silicos-IT LogSw": "silicosit_logsw",
    "Silicos-IT Solubility (mg/ml)": "silicosit_solubility_mg_ml",
    "Silicos-IT Solubility (mol/l)": "silicosit_solubility_mol_l",
    "Silicos-IT class": "silicosit_class",
    "GI absorption": "gi_absorption",
    "BBB permeant": "bbb_permeant",
    "Pgp substrate": "pgp_substrate",
    "CYP1A2 inhibitor": "cyp1a2_inhibitor",
    "CYP2C19 inhibitor": "cyp2c19_inhibitor",
    "CYP2C9 inhibitor": "cyp2c9_inhibitor",
    "CYP2D6 inhibitor": "cyp2d6_inhibitor",
    "CYP3A4 inhibitor": "cyp3a4_inhibitor",
    "log Kp (cm/s)": "log_kp",
    "Lipinski #violations": "lipinski_violations",
    "Ghose #violations": "ghose_violations",
    "Veber #violations": "veber_violations",
    "Egan #violations": "egan_violations",
    "Muegge #violations": "muegge_violations",
    "Bioavailability Score": "bioavailability_score",
    "PAINS #alerts": "pains_alerts",
    "Brenk #alerts": "brenk_alerts",
    "Leadlikeness #violations": "leadlikeness_violations",
    "Synthetic Accessibility": "synthetic_accessibility",
}

# Fields that should be parsed as floats
FLOAT_FIELDS = {
    "molecular_weight",
    "fraction_csp3",
    "molar_refractivity",
    "tpsa",
    "ilogp",
    "xlogp3",
    "wlogp",
    "mlogp",
    "silicosit_logp",
    "consensus_logp",
    "esol_logs",
    "esol_solubility_mg_ml",
    "esol_solubility_mol_l",
    "ali_logs",
    "ali_solubility_mg_ml",
    "ali_solubility_mol_l",
    "silicosit_logsw",
    "silicosit_solubility_mg_ml",
    "silicosit_solubility_mol_l",
    "log_kp",
    "bioavailability_score",
    "synthetic_accessibility",
}

# Fields that should be parsed as integers
INT_FIELDS = {
    "num_heavy_atoms",
    "num_aromatic_heavy_atoms",
    "num_rotatable_bonds",
    "num_hbond_acceptors",
    "num_hbond_donors",
    "lipinski_violations",
    "ghose_violations",
    "veber_violations",
    "egan_violations",
    "muegge_violations",
    "pains_alerts",
    "brenk_alerts",
    "leadlikeness_violations",
}

# Drug-likeness rule definitions (for check_druglikeness operation)
DRUGLIKENESS_RULES = {
    "lipinski": {
        "name": "Lipinski Rule of Five",
        "description": "MW <= 500, LogP <= 5, HBD <= 5, HBA <= 10",
        "violation_field": "lipinski_violations",
    },
    "ghose": {
        "name": "Ghose Filter",
        "description": "160 <= MW <= 480, -0.4 <= LogP <= 5.6, 40 <= MR <= 130, 20 <= atoms <= 70",
        "violation_field": "ghose_violations",
    },
    "veber": {
        "name": "Veber Rule",
        "description": "Rotatable bonds <= 10, TPSA <= 140",
        "violation_field": "veber_violations",
    },
    "egan": {
        "name": "Egan Rule",
        "description": "LogP <= 5.88, TPSA <= 131.6",
        "violation_field": "egan_violations",
    },
    "muegge": {
        "name": "Muegge Filter",
        "description": "200 <= MW <= 600, -2 <= LogP <= 5, TPSA <= 150, rings <= 7, HBA <= 10, HBD <= 5, rotatable bonds <= 15, carbons > 4",
        "violation_field": "muegge_violations",
    },
}


@register_tool("SwissADMETool")
class SwissADMETool(BaseTool):
    """
    Tool for computing ADMET properties and drug-likeness using SwissADME.

    Supported operations:
    - calculate_adme: Compute full ADMET property profile for a SMILES molecule
    - check_druglikeness: Quick drug-likeness filter check
    """

    def __init__(self, tool_config):
        # type: (Dict[str, Any]) -> None
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
        )

    def run(self, arguments):
        # type: (Dict[str, Any]) -> Dict[str, Any]
        """Execute the SwissADME tool with given arguments."""
        operation = arguments.get("operation")
        if not operation:
            return {
                "status": "error",
                "error": "Missing required parameter: operation",
            }

        operation_handlers = {
            "calculate_adme": self._calculate_adme,
            "check_druglikeness": self._check_druglikeness,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": "Unknown operation: {}. Available: {}".format(
                    operation, list(operation_handlers.keys())
                ),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": "SwissADME request timed out. The server may be busy.",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Could not connect to SwissADME. The service may be temporarily unavailable.",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": "SwissADME error: {}".format(str(e)),
            }

    def _submit_and_get_csv(self, smiles, name=None):
        # type: (str, Optional[str]) -> Optional[str]
        """
        Submit SMILES to SwissADME and retrieve the CSV results.

        Returns the CSV text content on success, or None on failure.
        """
        # Format input: "SMILES name" or just "SMILES"
        if name:
            smiles_input = "{} {}".format(smiles.strip(), name.strip())
        else:
            smiles_input = smiles.strip()

        # POST to the form
        resp = self.session.post(
            "{}/index.php".format(SWISSADME_BASE_URL),
            data={"smiles": smiles_input},
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": "{}/index.php".format(SWISSADME_BASE_URL),
                "Origin": SWISSADME_BASE_URL,
            },
            timeout=120,
        )

        if resp.status_code != 200:
            return None

        # Extract the CSV URL from the HTML response
        # Pattern: href="results/{job_id}/swissadme.csv"
        csv_match = re.search(
            r'href=["\'](?:results/(\d+)/swissadme\.csv)["\']', resp.text
        )
        if not csv_match:
            return None

        job_id = csv_match.group(1)
        csv_url = "{}/results/{}/swissadme.csv".format(SWISSADME_BASE_URL, job_id)

        # Fetch the CSV
        csv_resp = self.session.get(csv_url, timeout=30)
        if csv_resp.status_code != 200:
            return None

        return csv_resp.text

    def _parse_csv_row(self, csv_text):
        # type: (str) -> Optional[Dict[str, Any]]
        """Parse the CSV text into a structured dictionary."""
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = list(reader)
        if not rows:
            return None

        row = rows[0]
        result = {}

        for csv_header, key in CSV_FIELD_MAP.items():
            raw_value = row.get(csv_header, "").strip()
            if not raw_value:
                result[key] = None
                continue

            if key in FLOAT_FIELDS:
                try:
                    result[key] = float(raw_value)
                except (ValueError, TypeError):
                    result[key] = raw_value
            elif key in INT_FIELDS:
                try:
                    result[key] = int(raw_value)
                except (ValueError, TypeError):
                    result[key] = raw_value
            else:
                result[key] = raw_value

        return result

    def _calculate_adme(self, arguments):
        # type: (Dict[str, Any]) -> Dict[str, Any]
        """
        Compute full ADMET property profile for a SMILES molecule.

        Posts the SMILES to SwissADME, fetches the generated CSV result,
        and parses it into a structured dictionary with 49 properties.
        """
        smiles = arguments.get("smiles")
        if not smiles:
            return {"status": "error", "error": "Missing required parameter: smiles"}

        name = arguments.get("molecule_name")

        csv_text = self._submit_and_get_csv(smiles, name)
        if not csv_text:
            return {
                "status": "error",
                "error": "Failed to compute ADME properties for the given SMILES. "
                "Verify the SMILES is valid and represents a druglike small molecule.",
            }

        properties = self._parse_csv_row(csv_text)
        if not properties:
            return {
                "status": "error",
                "error": "Failed to parse SwissADME results.",
            }

        # Feature-26B-10: if SwissADME accepted an invalid SMILES, canonical_smiles
        # is null in the returned CSV. Treat this as a failure so users get a
        # clear error rather than a "success" response full of null values.
        if not properties.get("canonical_smiles"):
            return {
                "status": "error",
                "error": (
                    "SwissADME could not parse the given SMILES. "
                    "Verify the SMILES represents a valid small molecule "
                    "(e.g., 'CC(=O)Oc1ccccc1C(=O)O' for aspirin). "
                    "Get valid SMILES from PubChem or ChEMBL."
                ),
            }

        # Organize into categories for clarity
        data = {
            "molecule_name": properties.get("molecule_name"),
            "canonical_smiles": properties.get("canonical_smiles"),
            "physicochemical": {
                "formula": properties.get("formula"),
                "molecular_weight": properties.get("molecular_weight"),
                "num_heavy_atoms": properties.get("num_heavy_atoms"),
                "num_aromatic_heavy_atoms": properties.get("num_aromatic_heavy_atoms"),
                "fraction_csp3": properties.get("fraction_csp3"),
                "num_rotatable_bonds": properties.get("num_rotatable_bonds"),
                "num_hbond_acceptors": properties.get("num_hbond_acceptors"),
                "num_hbond_donors": properties.get("num_hbond_donors"),
                "molar_refractivity": properties.get("molar_refractivity"),
                "tpsa": properties.get("tpsa"),
            },
            "lipophilicity": {
                "ilogp": properties.get("ilogp"),
                "xlogp3": properties.get("xlogp3"),
                "wlogp": properties.get("wlogp"),
                "mlogp": properties.get("mlogp"),
                "silicosit_logp": properties.get("silicosit_logp"),
                "consensus_logp": properties.get("consensus_logp"),
            },
            "water_solubility": {
                "esol_logs": properties.get("esol_logs"),
                "esol_solubility_mg_ml": properties.get("esol_solubility_mg_ml"),
                "esol_solubility_mol_l": properties.get("esol_solubility_mol_l"),
                "esol_class": properties.get("esol_class"),
                "ali_logs": properties.get("ali_logs"),
                "ali_solubility_mg_ml": properties.get("ali_solubility_mg_ml"),
                "ali_solubility_mol_l": properties.get("ali_solubility_mol_l"),
                "ali_class": properties.get("ali_class"),
                "silicosit_logsw": properties.get("silicosit_logsw"),
                "silicosit_solubility_mg_ml": properties.get(
                    "silicosit_solubility_mg_ml"
                ),
                "silicosit_solubility_mol_l": properties.get(
                    "silicosit_solubility_mol_l"
                ),
                "silicosit_class": properties.get("silicosit_class"),
            },
            "pharmacokinetics": {
                "gi_absorption": properties.get("gi_absorption"),
                "bbb_permeant": properties.get("bbb_permeant"),
                "pgp_substrate": properties.get("pgp_substrate"),
                "cyp1a2_inhibitor": properties.get("cyp1a2_inhibitor"),
                "cyp2c19_inhibitor": properties.get("cyp2c19_inhibitor"),
                "cyp2c9_inhibitor": properties.get("cyp2c9_inhibitor"),
                "cyp2d6_inhibitor": properties.get("cyp2d6_inhibitor"),
                "cyp3a4_inhibitor": properties.get("cyp3a4_inhibitor"),
                "log_kp": properties.get("log_kp"),
            },
            "druglikeness": {
                "lipinski_violations": properties.get("lipinski_violations"),
                "ghose_violations": properties.get("ghose_violations"),
                "veber_violations": properties.get("veber_violations"),
                "egan_violations": properties.get("egan_violations"),
                "muegge_violations": properties.get("muegge_violations"),
                "bioavailability_score": properties.get("bioavailability_score"),
            },
            "medicinal_chemistry": {
                "pains_alerts": properties.get("pains_alerts"),
                "brenk_alerts": properties.get("brenk_alerts"),
                "leadlikeness_violations": properties.get("leadlikeness_violations"),
                "synthetic_accessibility": properties.get("synthetic_accessibility"),
            },
        }

        return {
            "status": "success",
            "data": data,
        }

    def _check_druglikeness(self, arguments):
        # type: (Dict[str, Any]) -> Dict[str, Any]
        """
        Quick drug-likeness filter check for a SMILES molecule.

        Computes ADME properties and evaluates drug-likeness rules.
        Optionally filters to specific rules.
        """
        smiles = arguments.get("smiles")
        if not smiles:
            return {"status": "error", "error": "Missing required parameter: smiles"}

        rules_filter = arguments.get("rules")

        csv_text = self._submit_and_get_csv(smiles)
        if not csv_text:
            return {
                "status": "error",
                "error": "Failed to compute properties for the given SMILES. "
                "Verify the SMILES is valid and represents a druglike small molecule.",
            }

        properties = self._parse_csv_row(csv_text)
        if not properties:
            return {
                "status": "error",
                "error": "Failed to parse SwissADME results.",
            }

        # Feature-26B-10: check for null canonical_smiles (invalid input)
        if not properties.get("canonical_smiles"):
            return {
                "status": "error",
                "error": (
                    "SwissADME could not parse the given SMILES. "
                    "Verify the SMILES represents a valid small molecule."
                ),
            }

        # Evaluate drug-likeness rules
        rules_to_check = DRUGLIKENESS_RULES
        if rules_filter:
            rules_to_check = {
                k: v for k, v in DRUGLIKENESS_RULES.items() if k in rules_filter
            }
            unknown = [r for r in rules_filter if r not in DRUGLIKENESS_RULES]
            if unknown:
                return {
                    "status": "error",
                    "error": "Unknown rules: {}. Valid: {}".format(
                        unknown, list(DRUGLIKENESS_RULES.keys())
                    ),
                }

        rule_results = {}
        passes_all = True
        for rule_key, rule_info in rules_to_check.items():
            violation_field = rule_info["violation_field"]
            violations = properties.get(violation_field, None)
            if violations is None:
                rule_results[rule_key] = {
                    "name": rule_info["name"],
                    "description": rule_info["description"],
                    "violations": None,
                    "passes": None,
                }
            else:
                passes = violations == 0
                if not passes:
                    passes_all = False
                rule_results[rule_key] = {
                    "name": rule_info["name"],
                    "description": rule_info["description"],
                    "violations": violations,
                    "passes": passes,
                }

        data = {
            "smiles": smiles,
            "canonical_smiles": properties.get("canonical_smiles"),
            "molecular_weight": properties.get("molecular_weight"),
            "consensus_logp": properties.get("consensus_logp"),
            "rules": rule_results,
            "passes_all_rules": passes_all,
            "bioavailability_score": properties.get("bioavailability_score"),
            "pains_alerts": properties.get("pains_alerts"),
            "brenk_alerts": properties.get("brenk_alerts"),
            "synthetic_accessibility": properties.get("synthetic_accessibility"),
        }

        return {
            "status": "success",
            "data": data,
        }
