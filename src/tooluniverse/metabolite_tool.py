"""
Metabolite tools for ToolUniverse.

Replaces the broken HMDB direct API (blocked by Cloudflare).
Uses PubChem as the primary compound data source and CTD for
disease associations.

Broken HMDB API archived at: src/tooluniverse/data/broken_apis/hmdb_rest.json
"""

import re
import requests
from typing import Any, Dict, List, Optional

from .base_tool import BaseTool
from .tool_registry import register_tool

PUBCHEM_API = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
CTD_API = "https://ctdbase.org/tools/batchQuery.go"

# Regex to strip common stereochemistry prefixes so CTD can match the parent compound.
# Example: "Beta-D-Glucose" → "Glucose", "L-Alanine" → "Alanine"
_STEREO_PREFIX = re.compile(
    r"^(alpha|beta|Alpha|Beta|D|L|R|S|cis|trans|endo|exo)[-\s]+"
    r"(alpha|beta|Alpha|Beta|D|L|R|S|cis|trans|endo|exo)?[-\s]*",
    re.IGNORECASE,
)

# CAS Registry Number pattern (e.g. 50-99-7)
_CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")


def _strip_stereo(name: str) -> str:
    """Remove leading stereochemistry descriptors from a compound name."""
    stripped = _STEREO_PREFIX.sub("", name).strip()
    return stripped if stripped and stripped != name else ""


def _cas_from_synonyms(synonyms: List[str]) -> Optional[str]:
    """Return the first CAS-style number (e.g. 50-99-7) from a synonyms list."""
    for s in synonyms:
        if _CAS_RE.match(s.strip()):
            return s.strip()
    return None


@register_tool("MetaboliteTool")
class MetaboliteTool(BaseTool):
    """
    Tool for querying metabolite data via PubChem (compound info) and
    CTD (disease associations).  Accepts HMDB IDs, compound names, and
    PubChem CIDs.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout: int = tool_config.get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation", "")
        if not operation:
            operation = self.get_schema_const_operation()

        if operation == "get_info":
            return self._get_info(arguments)
        elif operation == "search":
            return self._search(arguments)
        elif operation == "get_diseases":
            return self._get_diseases(arguments)
        return {
            "status": "error",
            "error": f"Unknown operation: {operation}. Supported: get_info, search, get_diseases",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_identifier(self, arguments: Dict[str, Any]) -> str:
        """Extract identifier from hmdb_id, compound_name, or pubchem_cid arguments."""
        identifier = (
            arguments.get("hmdb_id")
            or arguments.get("compound_name")
            or arguments.get("pubchem_cid")
            or ""
        )
        return str(identifier) if identifier else ""

    def _resolve_to_cid(self, identifier: str) -> Optional[int]:
        """
        Resolve an HMDB ID, compound name, or PubChem CID string to a CID integer.
        Returns None if resolution fails.
        """
        if identifier.lstrip("-").isdigit():
            return int(identifier)

        # HMDB ID → PubChem via RegistryID cross-reference
        if identifier.upper().startswith("HMDB"):
            hmdb_id = identifier.upper()
            if not re.match(r"^HMDB\d+$", hmdb_id):
                hmdb_id = f"HMDB{hmdb_id[4:].zfill(7)}"
            resp = requests.get(
                f"{PUBCHEM_API}/compound/xref/RegistryID/{hmdb_id}/JSON",
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                compounds = resp.json().get("PC_Compounds", [])
                if compounds:
                    return compounds[0].get("id", {}).get("id", {}).get("cid")
            return None

        # Compound name → PubChem CID (exact match first, then autocomplete fallback)
        resp = requests.get(
            f"{PUBCHEM_API}/compound/name/{requests.utils.quote(identifier)}/cids/JSON",
            timeout=self.timeout,
        )
        if resp.status_code == 200:
            cids = resp.json().get("IdentifierList", {}).get("CID", [])
            return cids[0] if cids else None
        # Autocomplete fallback for lipid classes and inexact names
        ac_resp = requests.get(
            f"https://pubchem.ncbi.nlm.nih.gov/rest/autocomplete/compound/{requests.utils.quote(identifier)}/json?limit=5",
            timeout=self.timeout,
        )
        if ac_resp.status_code == 200:
            suggestions = ac_resp.json().get("dictionary_terms", {}).get("compound", [])
            for suggestion in suggestions[:3]:
                cid_resp = requests.get(
                    f"{PUBCHEM_API}/compound/name/{requests.utils.quote(suggestion)}/cids/JSON",
                    timeout=self.timeout,
                )
                if cid_resp.status_code == 200:
                    cids = cid_resp.json().get("IdentifierList", {}).get("CID", [])
                    if cids:
                        return cids[0]
        return None

    def _get_properties(self, cid: int) -> Dict[str, Any]:
        """Fetch Title, IUPAC name, formula, weight, SMILES, InChIKey from PubChem."""
        resp = requests.get(
            f"{PUBCHEM_API}/compound/cid/{cid}/property/"
            "Title,MolecularFormula,MolecularWeight,IsomericSMILES,InChIKey,IUPACName/JSON",
            timeout=self.timeout,
        )
        if resp.status_code == 200:
            props = resp.json().get("PropertyTable", {}).get("Properties", [])
            return props[0] if props else {}
        return {}

    def _get_synonyms(self, cid: int) -> List[str]:
        """Fetch all synonyms for a PubChem CID."""
        resp = requests.get(
            f"{PUBCHEM_API}/compound/cid/{cid}/synonyms/JSON",
            timeout=self.timeout,
        )
        if resp.status_code == 200:
            info = resp.json().get("InformationList", {}).get("Information", [])
            return info[0].get("Synonym", []) if info else []
        return []

    def _ctd_diseases(self, chemical_term: str) -> List[Dict[str, Any]]:
        """Query CTD for curated disease associations for a chemical term."""
        resp = requests.get(
            CTD_API,
            params={
                "inputType": "chem",
                "inputTerms": chemical_term,
                "report": "diseases_curated",
                "format": "json",
            },
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        rows = data if isinstance(data, list) else []
        return [r for r in rows if isinstance(r, dict) and r.get("DiseaseName")]

    def _resolve_ctd_term(
        self, title: str, synonyms: List[str]
    ) -> tuple[str, List[Dict[str, Any]]]:
        """
        Try multiple name variants to find a CTD match.
        Returns (term_used, disease_rows).
        """
        candidates = [title]
        stripped = _strip_stereo(title)
        if stripped:
            candidates.append(stripped)
        cas = _cas_from_synonyms(synonyms)
        if cas:
            candidates.append(cas)
        # Also try common synonyms (e.g. "glucosylceramide" when title is "GlcCer(d18:1/...)")
        for syn in synonyms[:10]:
            if syn and syn not in candidates and len(syn) < 50 and not syn[0].isdigit():
                candidates.append(syn)

        for term in candidates:
            rows = self._ctd_diseases(term)
            if rows:
                return term, rows
        return candidates[0], []

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------

    def _get_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get compound info for a metabolite by HMDB ID, compound name, or PubChem CID.
        Returns common name, IUPAC name, formula, weight, SMILES, InChIKey.
        """
        identifier = self._extract_identifier(arguments)
        if not identifier:
            return {
                "status": "error",
                "error": "Provide hmdb_id, compound_name, or pubchem_cid.",
            }
        try:
            cid = self._resolve_to_cid(identifier)
            if cid is None:
                return {
                    "status": "error",
                    "error": f"Could not resolve '{identifier}' to a PubChem compound.",
                }
            props = self._get_properties(cid)
            return {
                "status": "success",
                "data": {
                    "pubchem_cid": cid,
                    "name": props.get("Title"),
                    "iupac_name": props.get("IUPACName"),
                    "formula": props.get("MolecularFormula"),
                    "molecular_weight": props.get("MolecularWeight"),
                    "smiles": props.get("SMILES") or props.get("IsomericSMILES"),
                    "inchikey": props.get("InChIKey"),
                },
                "metadata": {
                    "source": "PubChem",
                    "pubchem_url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
                },
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for metabolites by name or molecular formula.
        Returns up to 10 PubChem compounds with name, formula, weight, SMILES.
        """
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "Missing required parameter: query"}

        search_type = arguments.get("search_type", "name")
        limit = max(1, min(int(arguments.get("limit", 10)), 50))
        try:
            if search_type == "formula":
                url = f"{PUBCHEM_API}/compound/fastformula/{requests.utils.quote(query)}/property/Title,MolecularFormula,MolecularWeight,CanonicalSMILES/JSON"
                resp = requests.get(url, timeout=self.timeout)
                cids_to_fetch: list[int] = []
                if resp.status_code == 200:
                    for p in (
                        resp.json()
                        .get("PropertyTable", {})
                        .get("Properties", [])[:limit]
                    ):
                        cids_to_fetch.append(p.get("CID"))
            else:
                # Try exact name first; fall back to PubChem keyword search on miss
                exact_url = f"{PUBCHEM_API}/compound/name/{requests.utils.quote(query)}/cids/JSON"
                resp = requests.get(exact_url, timeout=self.timeout)
                if resp.status_code == 200:
                    cids_to_fetch = (
                        resp.json().get("IdentifierList", {}).get("CID", [])[:limit]
                    )
                else:
                    # Keyword fallback via PubChem autocomplete → fastsimilarity is not
                    # available without a structure; use the compound keyword search instead
                    kw_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/autocomplete/compound/{requests.utils.quote(query)}/json?limit={limit}"
                    kw_resp = requests.get(kw_url, timeout=self.timeout)
                    cids_to_fetch = []
                    if kw_resp.status_code == 200:
                        suggestions = (
                            kw_resp.json()
                            .get("dictionary_terms", {})
                            .get("compound", [])
                        )
                        for suggestion in suggestions[:5]:
                            cid_resp = requests.get(
                                f"{PUBCHEM_API}/compound/name/{requests.utils.quote(suggestion)}/cids/JSON",
                                timeout=self.timeout,
                            )
                            if cid_resp.status_code == 200:
                                cids = (
                                    cid_resp.json()
                                    .get("IdentifierList", {})
                                    .get("CID", [])
                                )
                                cids_to_fetch.extend(cids[:2])
                        cids_to_fetch = list(dict.fromkeys(cids_to_fetch))[:limit]

            results = []
            if cids_to_fetch:
                cid_str = ",".join(str(c) for c in cids_to_fetch)
                prop_url = f"{PUBCHEM_API}/compound/cid/{cid_str}/property/Title,MolecularFormula,MolecularWeight,IsomericSMILES/JSON"
                prop_resp = requests.get(prop_url, timeout=self.timeout)
                if prop_resp.status_code == 200:
                    for p in (
                        prop_resp.json().get("PropertyTable", {}).get("Properties", [])
                    ):
                        results.append(
                            {
                                "pubchem_cid": p.get("CID"),
                                "name": p.get("Title"),
                                "formula": p.get("MolecularFormula"),
                                "molecular_weight": p.get("MolecularWeight"),
                                "smiles": p.get("SMILES") or p.get("IsomericSMILES"),
                            }
                        )
            return {
                "status": "success",
                "data": {"query": query, "results": results, "count": len(results)},
                "metadata": {"source": "PubChem"},
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}

    def _get_diseases(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get curated disease associations for a metabolite.

        Accepts HMDB ID, compound name, or PubChem CID. Resolves to a
        PubChem compound, then queries CTD with multiple name variants
        (title, stereo-stripped, CAS number) to maximise CTD match rate.
        """
        identifier = self._extract_identifier(arguments)
        if not identifier:
            return {
                "status": "error",
                "error": "Provide hmdb_id, compound_name, or pubchem_cid.",
            }
        limit = int(arguments.get("limit", 50))

        try:
            cid = self._resolve_to_cid(identifier)
            if cid is None:
                return {
                    "status": "error",
                    "error": f"Could not resolve '{identifier}' to a PubChem compound.",
                }

            props = self._get_properties(cid)
            title = props.get("Title") or props.get("IUPACName", identifier)
            synonyms = self._get_synonyms(cid)

            # Prepend the original user input as the first candidate for CTD resolution
            # (e.g. "glucocerebroside" is recognized by CTD even if PubChem title is "GlcCer(d18:1/...)")
            if (
                identifier
                and not identifier.upper().startswith("HMDB")
                and not identifier.isdigit()
                and identifier != title
            ):
                synonyms = [identifier] + list(synonyms)
            term_used, rows = self._resolve_ctd_term(title, synonyms)
            diseases = [
                {
                    "disease_name": r.get("DiseaseName"),
                    "disease_id": r.get("DiseaseID"),
                    "disease_categories": r.get("DiseaseCategories"),
                    "direct_evidence": r.get("DirectEvidence"),
                    "pubmed_ids": (
                        r["PubMedIDs"].split("|") if r.get("PubMedIDs") else []
                    ),
                }
                for r in rows
            ][:limit]

            return {
                "status": "success",
                "data": {
                    "identifier": identifier,
                    "compound_name": title,
                    "pubchem_cid": cid,
                    "ctd_query_term": term_used,
                    "disease_count": len(diseases),
                    "diseases": diseases,
                },
                "metadata": {
                    "source": "CTD (Comparative Toxicogenomics Database)",
                    "pubchem_url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
                },
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
