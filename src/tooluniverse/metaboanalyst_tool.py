"""
MetaboAnalyst-style metabolomics analysis tool for ToolUniverse.

Provides metabolite name mapping, pathway enrichment analysis,
pathway library browsing, and metabolite set (biomarker) enrichment.

Uses the KEGG REST API (https://rest.kegg.jp/) for compound resolution
and pathway-metabolite mappings, and performs statistical enrichment
(hypergeometric / Fisher's exact test) locally via scipy.

No authentication required.
"""

import re
import requests
from math import log2
from typing import Any, Dict, List, Optional, Tuple

from .base_tool import BaseTool
from .tool_registry import register_tool

try:
    from scipy.stats import hypergeom

    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

KEGG_BASE = "https://rest.kegg.jp"

# ------------------------------------------------------------------
# Curated metabolite-set libraries for biomarker enrichment
# Each set: name -> list of common metabolite names
# Derived from SMPDB/HMDB pathway categories
# ------------------------------------------------------------------
BIOMARKER_SETS: Dict[str, List[str]] = {
    "Glycolysis and Gluconeogenesis": [
        "glucose",
        "pyruvate",
        "lactate",
        "fructose 1,6-bisphosphate",
        "glyceraldehyde 3-phosphate",
        "dihydroxyacetone phosphate",
        "phosphoenolpyruvate",
        "2-phosphoglycerate",
        "3-phosphoglycerate",
        "glucose 6-phosphate",
        "fructose 6-phosphate",
    ],
    "TCA Cycle": [
        "citrate",
        "isocitrate",
        "alpha-ketoglutarate",
        "succinate",
        "fumarate",
        "malate",
        "oxaloacetate",
        "pyruvate",
        "acetyl-CoA",
    ],
    "Urea Cycle": [
        "ornithine",
        "citrulline",
        "argininosuccinate",
        "arginine",
        "urea",
        "fumarate",
        "aspartate",
    ],
    "Amino Acid Metabolism": [
        "alanine",
        "glycine",
        "serine",
        "threonine",
        "valine",
        "leucine",
        "isoleucine",
        "proline",
        "phenylalanine",
        "tyrosine",
        "tryptophan",
        "aspartate",
        "glutamate",
        "lysine",
        "histidine",
        "methionine",
        "cysteine",
        "arginine",
        "asparagine",
        "glutamine",
    ],
    "Fatty Acid Biosynthesis": [
        "palmitic acid",
        "stearic acid",
        "oleic acid",
        "myristic acid",
        "lauric acid",
        "malonyl-CoA",
        "acetyl-CoA",
    ],
    "Fatty Acid Beta-Oxidation": [
        "palmitic acid",
        "palmitoylcarnitine",
        "acetyl-CoA",
        "octanoylcarnitine",
        "hexanoylcarnitine",
        "butyrylcarnitine",
        "acetylcarnitine",
        "carnitine",
    ],
    "Purine Metabolism": [
        "adenine",
        "guanine",
        "hypoxanthine",
        "xanthine",
        "uric acid",
        "inosine",
        "adenosine",
        "guanosine",
        "AMP",
        "GMP",
        "IMP",
    ],
    "Pyrimidine Metabolism": [
        "uracil",
        "thymine",
        "cytosine",
        "uridine",
        "thymidine",
        "cytidine",
        "UMP",
        "CMP",
        "orotate",
    ],
    "Glutathione Metabolism": [
        "glutathione",
        "glutamate",
        "cysteine",
        "glycine",
        "gamma-glutamylcysteine",
        "pyroglutamic acid",
        "5-oxoproline",
    ],
    "Tryptophan Metabolism": [
        "tryptophan",
        "kynurenine",
        "serotonin",
        "melatonin",
        "3-hydroxykynurenine",
        "quinolinic acid",
        "nicotinamide",
        "indole",
        "indole-3-acetic acid",
    ],
    "Bile Acid Biosynthesis": [
        "cholesterol",
        "cholic acid",
        "chenodeoxycholic acid",
        "deoxycholic acid",
        "lithocholic acid",
        "glycocholic acid",
        "taurocholic acid",
        "ursodeoxycholic acid",
    ],
    "Ketone Body Metabolism": [
        "acetoacetate",
        "3-hydroxybutyrate",
        "acetone",
        "acetyl-CoA",
    ],
    "Pentose Phosphate Pathway": [
        "glucose 6-phosphate",
        "6-phosphogluconate",
        "ribulose 5-phosphate",
        "ribose 5-phosphate",
        "xylulose 5-phosphate",
        "sedoheptulose 7-phosphate",
        "erythrose 4-phosphate",
        "fructose 6-phosphate",
        "glyceraldehyde 3-phosphate",
    ],
    "Sphingolipid Metabolism": [
        "sphingosine",
        "sphinganine",
        "ceramide",
        "sphingomyelin",
        "sphingosine 1-phosphate",
        "palmitoyl-CoA",
        "serine",
    ],
    "Arachidonic Acid Metabolism": [
        "arachidonic acid",
        "prostaglandin E2",
        "prostaglandin F2alpha",
        "thromboxane A2",
        "leukotriene B4",
        "leukotriene C4",
        "5-HETE",
        "12-HETE",
        "15-HETE",
    ],
    "Branched-Chain Amino Acid Degradation": [
        "valine",
        "leucine",
        "isoleucine",
        "alpha-ketoisovalerate",
        "alpha-ketoisocaproate",
        "alpha-keto-beta-methylvalerate",
        "isobutyryl-CoA",
        "isovaleryl-CoA",
        "methylbutyryl-CoA",
    ],
    "Histidine Metabolism": [
        "histidine",
        "histamine",
        "imidazole acetaldehyde",
        "urocanate",
        "glutamate",
        "methylhistidine",
    ],
    "Methionine and Cysteine Metabolism": [
        "methionine",
        "S-adenosylmethionine",
        "S-adenosylhomocysteine",
        "homocysteine",
        "cysteine",
        "cystathionine",
        "taurine",
    ],
    "Nicotinate and Nicotinamide Metabolism": [
        "nicotinamide",
        "nicotinate",
        "NAD+",
        "NADP+",
        "nicotinamide mononucleotide",
        "nicotinic acid mononucleotide",
        "quinolinic acid",
    ],
    "Pantothenate and CoA Biosynthesis": [
        "pantothenate",
        "pantetheine",
        "coenzyme A",
        "4-phosphopantothenate",
        "beta-alanine",
        "cysteine",
    ],
}


def _normalize(name: str) -> str:
    """Lowercase, strip whitespace, remove trailing acid/ate variants for matching."""
    return re.sub(r"\s+", " ", name.strip().lower())


@register_tool("MetaboAnalystTool")
class MetaboAnalystTool(BaseTool):
    """
    Metabolomics analysis tool providing metabolite name mapping,
    pathway enrichment, pathway library listing, and biomarker
    set enrichment.  Uses KEGG REST API + local scipy statistics.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "pathway_enrichment")

    # ----------------------------------------------------------
    # dispatch
    # ----------------------------------------------------------
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "KEGG API timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Cannot connect to KEGG API"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if self.endpoint == "pathway_enrichment":
            return self._pathway_enrichment(arguments)
        elif self.endpoint == "name_to_id":
            return self._name_to_id(arguments)
        elif self.endpoint == "get_pathway_library":
            return self._get_pathway_library(arguments)
        elif self.endpoint == "biomarker_enrichment":
            return self._biomarker_enrichment(arguments)
        return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    # ----------------------------------------------------------
    # helpers – KEGG API wrappers
    # ----------------------------------------------------------
    def _kegg_find_compound(self, name: str) -> Optional[Tuple[str, str]]:
        """Resolve a metabolite name to (KEGG compound ID, matched name).
        Returns the first exact-ish hit or None."""
        url = f"{KEGG_BASE}/find/compound/{requests.utils.quote(name)}"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code != 200 or not resp.text.strip():
            return None
        norm = _normalize(name)
        # Try exact match first
        for line in resp.text.strip().split("\n"):
            parts = line.split("\t", 1)
            if len(parts) < 2:
                continue
            cid = parts[0].replace("cpd:", "")
            synonyms = [_normalize(s) for s in parts[1].split(";")]
            for syn in synonyms:
                if syn == norm:
                    return (cid, parts[1].split(";")[0].strip())
        # Feature-71A-003: No blind fallback to first result — only return exact match or None
        return None

    def _kegg_get_compound_info(self, compound_id: str) -> Dict[str, Any]:
        """Get compound detail from KEGG (name, formula, exact mass, etc.)."""
        url = f"{KEGG_BASE}/get/{compound_id}"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code != 200:
            return {}
        info: Dict[str, Any] = {"kegg_id": compound_id}
        for line in resp.text.split("\n"):
            if line.startswith("NAME"):
                names_part = line[12:].strip()
                info["name"] = names_part.rstrip(";").split(";")[0].strip()
            elif line.startswith("FORMULA"):
                info["formula"] = line[12:].strip()
            elif line.startswith("EXACT_MASS"):
                try:
                    info["exact_mass"] = float(line[12:].strip())
                except ValueError:
                    pass
            elif line.startswith("MOL_WEIGHT"):
                try:
                    info["mol_weight"] = float(line[12:].strip())
                except ValueError:
                    pass
            elif line.startswith("DBLINKS"):
                info["dblinks"] = self._parse_dblinks(line, resp.text)
        return info

    @staticmethod
    def _parse_dblinks(first_line: str, full_text: str) -> Dict[str, str]:
        """Parse DBLINKS section from KEGG flat-file format."""
        links: Dict[str, str] = {}
        in_dblinks = False
        for line in full_text.split("\n"):
            if line.startswith("DBLINKS"):
                in_dblinks = True
                content = line[12:].strip()
            elif in_dblinks:
                if line.startswith(" ") or line.startswith("\t"):
                    content = line.strip()
                else:
                    break
            else:
                continue
            if in_dblinks and content:
                parts = content.split(":", 1)
                if len(parts) == 2:
                    db = parts[0].strip()
                    ids = parts[1].strip()
                    links[db] = ids
        return links

    def _kegg_list_pathways(self, organism: str) -> List[Dict[str, str]]:
        """List all KEGG pathways for an organism."""
        url = f"{KEGG_BASE}/list/pathway/{organism}"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code != 200:
            return []
        pathways = []
        for line in resp.text.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                pid = parts[0].strip()
                pname = parts[1].strip()
                # Remove organism suffix like " - Homo sapiens (human)"
                pname = re.sub(r"\s+-\s+[A-Z][a-z].*$", "", pname)
                pathways.append({"pathway_id": pid, "pathway_name": pname})
        return pathways

    def _kegg_get_pathway_compounds(self, pathway_map_id: str) -> List[str]:
        """Get KEGG compound IDs in a pathway (using map prefix)."""
        url = f"{KEGG_BASE}/link/cpd/{pathway_map_id}"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code != 200 or not resp.text.strip():
            return []
        compounds = []
        for line in resp.text.strip().split("\n"):
            parts = line.split("\t")
            if len(parts) >= 2:
                cid = parts[1].replace("cpd:", "")
                compounds.append(cid)
        return compounds

    # ----------------------------------------------------------
    # 1. Pathway Enrichment
    # ----------------------------------------------------------
    def _pathway_enrichment(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not HAS_SCIPY:
            return {
                "status": "error",
                "error": "scipy is required for enrichment analysis. Install: pip install scipy",
            }

        metabolites = arguments.get("metabolites", [])
        if not metabolites or not isinstance(metabolites, list):
            return {
                "status": "error",
                "error": "metabolites must be a non-empty list of metabolite names",
            }
        organism = arguments.get("organism", "hsa")

        # Step 1: resolve metabolite names to KEGG compound IDs
        resolved = {}
        unresolved = []
        for name in metabolites:
            result = self._kegg_find_compound(name)
            if result:
                resolved[name] = result[0]  # compound ID
            else:
                unresolved.append(name)

        if not resolved:
            return {
                "status": "error",
                "error": f"Could not resolve any metabolite names to KEGG IDs. Tried: {metabolites}",
            }

        query_cids = set(resolved.values())

        # Step 2: get metabolic pathway list (filter to metabolic pathways)
        all_pathways = self._kegg_list_pathways(organism)
        # Focus on metabolic pathways (IDs 00xxx and 01xxx)
        metabolic_pathways = []
        for pw in all_pathways:
            pid = pw["pathway_id"]
            num_part = re.sub(r"^[a-z]+", "", pid)
            if num_part.isdigit():
                num = int(num_part)
                # Metabolic pathways: 00010-01999
                if num < 2000:
                    metabolic_pathways.append(pw)

        if not metabolic_pathways:
            return {
                "status": "error",
                "error": f"No metabolic pathways found for organism '{organism}'",
            }

        # Step 3: build pathway-compound map (use map prefix for compound links)
        pathway_compounds: Dict[str, List[str]] = {}
        for pw in metabolic_pathways:
            pid = pw["pathway_id"]
            map_id = "map" + re.sub(r"^[a-z]+", "", pid)
            compounds = self._kegg_get_pathway_compounds(map_id)
            if compounds:
                pathway_compounds[pid] = compounds

        # Step 4: collect background (all unique compounds across all pathways)
        all_compounds = set()
        for cids in pathway_compounds.values():
            all_compounds.update(cids)
        N = len(all_compounds)  # total background size

        if N == 0:
            return {
                "status": "error",
                "error": "No compound data found for pathways",
            }

        k = len(query_cids)  # query set size

        # Step 5: hypergeometric enrichment
        results = []
        for pw in metabolic_pathways:
            pid = pw["pathway_id"]
            if pid not in pathway_compounds:
                continue
            pw_cids = set(pathway_compounds[pid])
            m = len(pw_cids)  # pathway size
            overlap = query_cids & pw_cids
            x = len(overlap)  # overlap size
            if x == 0:
                continue
            # P(X >= x) using hypergeometric survival function
            p_value = hypergeom.sf(x - 1, N, m, k)
            fold_enrichment = (x / k) / (m / N) if m > 0 and k > 0 and N > 0 else 0

            results.append(
                {
                    "pathway_id": pid,
                    "pathway_name": pw["pathway_name"],
                    "p_value": round(p_value, 6),
                    "fold_enrichment": round(fold_enrichment, 2),
                    "hit_count": x,
                    "pathway_size": m,
                    "hit_metabolites": sorted(overlap),
                }
            )

        # Sort by p-value
        results.sort(key=lambda r: r["p_value"])

        # Apply simple Benjamini-Hochberg FDR correction
        n_tests = len(results)
        for i, r in enumerate(results):
            rank = i + 1
            fdr = r["p_value"] * n_tests / rank
            r["fdr"] = round(min(fdr, 1.0), 6)

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "organism": organism,
                "query_count": len(metabolites),
                "resolved_count": len(resolved),
                "unresolved": unresolved if unresolved else None,
                "background_size": N,
                "pathways_tested": n_tests,
                "method": "hypergeometric (over-representation analysis)",
                "source": "KEGG",
            },
        }

    # ----------------------------------------------------------
    # 2. Name to ID mapping
    # ----------------------------------------------------------
    def _name_to_id(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        metabolites = arguments.get("metabolites", [])
        if not metabolites or not isinstance(metabolites, list):
            return {
                "status": "error",
                "error": "metabolites must be a non-empty list of metabolite names",
            }

        results = []
        for name in metabolites:
            entry: Dict[str, Any] = {"query": name, "match": None}
            hit = self._kegg_find_compound(name)
            if hit:
                cid, matched_name = hit
                entry["match"] = matched_name
                entry["kegg_id"] = cid
                # Get additional DB cross-references
                info = self._kegg_get_compound_info(cid)
                dblinks = info.get("dblinks", {})
                entry["hmdb_id"] = dblinks.get("HMDB", None)
                entry["pubchem_sid"] = dblinks.get("PubChem", None)
                entry["chebi_id"] = dblinks.get("ChEBI", None)
                entry["formula"] = info.get("formula", None)
                entry["exact_mass"] = info.get("exact_mass", None)
            else:
                entry["kegg_id"] = None
                entry["hmdb_id"] = None
                entry["pubchem_sid"] = None
                entry["chebi_id"] = None
                entry["formula"] = None
                entry["exact_mass"] = None
            results.append(entry)

        return {
            "status": "success",
            "data": results,
        }

    # ----------------------------------------------------------
    # 3. Pathway library listing
    # ----------------------------------------------------------
    def _get_pathway_library(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        organism = arguments.get("organism", "hsa")

        all_pathways = self._kegg_list_pathways(organism)
        if not all_pathways:
            return {
                "status": "error",
                "error": f"No pathways found for organism '{organism}'. Use KEGG organism code (hsa=human, mmu=mouse, rno=rat, dme=fly, sce=yeast).",
            }

        # Enrich with compound counts for metabolic pathways
        results = []
        for pw in all_pathways:
            pid = pw["pathway_id"]
            num_part = re.sub(r"^[a-z]+", "", pid)
            is_metabolic = False
            if num_part.isdigit():
                num = int(num_part)
                is_metabolic = num < 2000

            entry = {
                "pathway_id": pid,
                "pathway_name": pw["pathway_name"],
                "category": "metabolic" if is_metabolic else "non-metabolic",
            }

            if is_metabolic:
                map_id = "map" + num_part
                compounds = self._kegg_get_pathway_compounds(map_id)
                entry["compound_count"] = len(compounds)
            else:
                entry["compound_count"] = 0

            results.append(entry)

        # Sort: metabolic first, then by compound count
        results.sort(
            key=lambda r: (
                -1 if r["category"] == "metabolic" else 0,
                -r["compound_count"],
            )
        )

        metabolic_count = sum(1 for r in results if r["category"] == "metabolic")
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "organism": organism,
                "total_pathways": len(results),
                "metabolic_pathways": metabolic_count,
                "source": "KEGG",
            },
        }

    # ----------------------------------------------------------
    # 4. Biomarker / metabolite-set enrichment
    # ----------------------------------------------------------
    def _biomarker_enrichment(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not HAS_SCIPY:
            return {
                "status": "error",
                "error": "scipy is required for enrichment analysis. Install: pip install scipy",
            }

        metabolites = arguments.get("metabolites", [])
        if not metabolites or not isinstance(metabolites, list):
            return {
                "status": "error",
                "error": "metabolites must be a non-empty list of metabolite names",
            }

        query_set = {_normalize(m) for m in metabolites}

        # Build background: union of all metabolites across all sets
        all_metabolites_set = set()
        for mset in BIOMARKER_SETS.values():
            for m in mset:
                all_metabolites_set.add(_normalize(m))
        # Also add query metabolites to background
        all_metabolites_set.update(query_set)

        N = len(all_metabolites_set)  # background size
        k = len(query_set)  # query size

        results = []
        for set_name, set_members in BIOMARKER_SETS.items():
            normalized_members = {_normalize(m) for m in set_members}
            m = len(normalized_members)  # set size
            overlap = query_set & normalized_members
            x = len(overlap)

            if x == 0:
                continue

            p_value = hypergeom.sf(x - 1, N, m, k)
            fold_enrichment = (x / k) / (m / N) if m > 0 and k > 0 and N > 0 else 0

            results.append(
                {
                    "metabolite_set": set_name,
                    "p_value": round(p_value, 6),
                    "fold_enrichment": round(fold_enrichment, 2),
                    "hit_count": x,
                    "set_size": m,
                    "hit_metabolites": sorted(overlap),
                }
            )

        results.sort(key=lambda r: r["p_value"])

        # BH FDR correction
        n_tests = len(results)
        for i, r in enumerate(results):
            rank = i + 1
            fdr = r["p_value"] * n_tests / rank
            r["fdr"] = round(min(fdr, 1.0), 6)

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "query_count": len(metabolites),
                "background_size": N,
                "sets_tested": len(BIOMARKER_SETS),
                "sets_hit": len(results),
                "library": "MetaboAnalyst-style SMPDB/HMDB metabolite sets",
                "method": "hypergeometric (over-representation analysis)",
            },
        }
