import os
import re
import requests
from typing import Any, Dict, List, Tuple
from difflib import SequenceMatcher

from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("CellosaurusSearchTool")
class CellosaurusSearchTool(BaseTool):
    """
    Tool to search Cellosaurus cell lines using the official API.
    """

    def __init__(self, tool_config, base_url="https://api.cellosaurus.org"):
        super().__init__(tool_config)
        self.base_url = base_url
        self.timeout_seconds = int(os.environ.get("CELLOSAURUS_TIMEOUT", "30"))

    def run(self, arguments):
        q = arguments.get("q")
        offset = arguments.get("offset", 0)
        size = arguments.get("size", 20)

        if not q:
            return {"status": "error", "error": "`q` parameter is required."}

        return self._search_cell_lines(q, offset, size)

    def _search_cell_lines(self, query, offset, size):
        """
        Search Cellosaurus cell lines using the /search/cell-line endpoint.
        """
        try:
            params = {"q": query.strip(), "offset": offset, "size": size}

            url = f"{self.base_url}/search/cell-line"
            headers = {"Accept": "application/json"}
            resp = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            data = resp.json()

            # Extract cell lines from the API response structure
            cell_lines = []
            total_count = 0

            if isinstance(data, dict) and "Cellosaurus" in data:
                cellosaurus_data = data["Cellosaurus"]
                if "cell-line-list" in cellosaurus_data:
                    cell_lines = cellosaurus_data["cell-line-list"]
                    total_count = len(cell_lines)

            return {
                "success": True,
                "results": {
                    "cell_lines": cell_lines,
                    "total": total_count,
                    "offset": offset,
                    "size": size,
                },
                "query": query.strip(),
            }
        except requests.HTTPError as http_err:
            status = getattr(http_err.response, "status_code", None)
            return {"status": "error", "error": f"HTTP {status}: {http_err}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}


@register_tool("CellosaurusQueryConverterTool")
class CellosaurusQueryConverterTool(BaseTool):
    """
    Tool to convert natural language queries to Solr syntax for
    Cellosaurus API.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)

        # Complete Cellosaurus field definitions from official API
        # documentation
        # https://api.cellosaurus.org/api-fields
        self.cellosaurus_fields = {
            "id": {
                "short_name": "-",
                "description": (
                    "Recommended name. Most frequently the name of the cell "
                    "line as provided in the original publication."
                ),
                "keywords": [
                    "name",
                    "cell line",
                    "cellline",
                    "recommended",
                    "publication",
                ],
            },
            "sy": {
                "short_name": "-",
                "description": (
                    "List of synonyms. We try to list all the different "
                    "synonyms for the cell line, including alternative use of "
                    "lower and upper cases characters. Misspellings are not "
                    'included in synonyms (see the "misspelling" tag).'
                ),
                "keywords": [
                    "synonym",
                    "synonyms",
                    "alias",
                    "alternative",
                    "different names",
                ],
            },
            "idsy": {
                "short_name": "-",
                "description": (
                    "Recommended name with all its synonyms. Concatenation of "
                    "ID and SY."
                ),
                "keywords": [
                    "name",
                    "synonyms",
                    "combined",
                    "concatenation",
                ],
            },
            "ac": {
                "short_name": "-",
                "description": (
                    "Primary accession. It is the unique identifier of the "
                    "cell line. It is normally stable across Cellosaurus "
                    "versions but when two entries are merged, one of the two "
                    "accessions stays primary while the second one becomes "
                    "secondary (see ACAS)"
                ),
                "keywords": [
                    "accession",
                    "primary",
                    "identifier",
                    "unique",
                    "stable",
                ],
            },
            "acas": {
                "short_name": "-",
                "description": (
                    "Primary and secondary accession. Secondary accession are "
                    "former primary accession kept here to ensure the access "
                    "to a cell line via old identifiers."
                ),
                "keywords": [
                    "accession",
                    "primary",
                    "secondary",
                    "former",
                    "old identifiers",
                ],
            },
            "dr": {
                "short_name": "-",
                "description": (
                    "Cross-references to external resources: cell catalogs, "
                    "databases, resources listing cell lines as samples or to "
                    "ontologies. A cross-reference has two parts: the short "
                    "name of the resource (i.e. CCLE) and an identifier used "
                    "to locate a particular entry of the resource related to "
                    "the cell line. For a formal description of all the "
                    "resources referred to in Cellosaurus, see here ."
                ),
                "keywords": [
                    "cross-reference",
                    "external",
                    "catalog",
                    "database",
                    "atcc",
                    "dsmz",
                    "ccle",
                    "ecacc",
                ],
            },
            "ref": {
                "short_name": "-",
                "description": (
                    "Publication references. Mostly publications describing "
                    "the establishment of a cell line or its "
                    "characterization. Can be journal articles, book "
                    "chapters, patents and theses. Contains the "
                    "cross-reference of the publication, its title, authors "
                    "(or group/consortium) and citation elements."
                ),
                "keywords": [
                    "reference",
                    "publication",
                    "paper",
                    "article",
                    "journal",
                    "book",
                    "patent",
                    "thesis",
                ],
            },
            "rx": {
                "short_name": "-",
                "description": (
                    "Publication cross-reference. A unique identifier "
                    "allowing access the publication online. The "
                    "cross-reference has two parts: the shortname of the "
                    "online resource (i.e. PubMed, DOI, PMCID, CLPUB) "
                    "and an identifier used to locate the particular "
                    "publication related to the cell line. For a formal "
                    "description of all the resources referred to in "
                    "Cellosaurus, see here ."
                ),
                "keywords": [
                    "cross-reference",
                    "online",
                    "pubmed",
                    "doi",
                    "pmcid",
                    "clpub",
                    "patent",
                    "identifier",
                ],
            },
            "ra": {
                "short_name": "-",
                "description": (
                    "Publication authors. List of authors of a publication "
                    "referenced in a cell line entry."
                ),
                "keywords": [
                    "author",
                    "authors",
                    "written by",
                    "publication",
                ],
            },
            "rt": {
                "short_name": "-",
                "description": (
                    "Publication title. Title of a publication referenced in "
                    "cell line entry."
                ),
                "keywords": ["title", "paper", "article", "publication"],
            },
            "rl": {
                "short_name": "-",
                "description": (
                    "Publication citation elements. Citation elements of a "
                    "publication referenced in a cell line entry."
                ),
                "keywords": ["citation", "cite", "reference", "elements"],
            },
            "ww": {
                "short_name": "-",
                "description": "Web page related to the cell line",
                "keywords": ["website", "web page", "homepage", "url"],
            },
            "anc": {
                "short_name": "genome-ancestry",
                "description": (
                    "Estimated ethnic ancestry of the donor of a human cell "
                    "line based on the analysis of its genome."
                ),
                "keywords": [
                    "ancestry",
                    "ethnic",
                    "genetic background",
                    "genome",
                    "donor",
                ],
            },
            "hla": {
                "short_name": "-",
                "description": (
                    "HLA typing information. Alleles identified on the MHC "
                    "type I and type II genes of the donor of a human cell "
                    "line."
                ),
                "keywords": [
                    "hla",
                    "mhc",
                    "typing",
                    "alleles",
                    "genes",
                    "donor",
                ],
            },
            "reg": {
                "short_name": "registration",
                "description": (
                    "Official list, or register in which the cell line is registered."
                ),
                "keywords": [
                    "registration",
                    "registered",
                    "official",
                    "register",
                ],
            },
            "var": {
                "short_name": "sequence-variation",
                "description": (
                    "Important sequence variations of the cell line compared "
                    "to the reference genome of the species."
                ),
                "keywords": [
                    "variation",
                    "mutation",
                    "sequence",
                    "variant",
                    "snv",
                    "indel",
                ],
            },
            "anec": {
                "short_name": "anecdotal",
                "description": (
                    "Anecdotal details regarding the cell line (its origin, "
                    "its name or any other particularity)."
                ),
                "keywords": [
                    "anecdotal",
                    "story",
                    "history",
                    "background",
                    "origin",
                ],
            },
            "biot": {
                "short_name": "biotechnology",
                "description": (
                    "Type of use of the cell line in a biotechnological context."
                ),
                "keywords": [
                    "biotechnology",
                    "biotech",
                    "production",
                    "manufacturing",
                    "use",
                ],
            },
            "breed": {
                "short_name": "-",
                "description": (
                    "Breed or subspecies an animal cell line is derived from "
                    "with breed identifiers from FlyBase_Strain, RS and VBO."
                ),
                "keywords": [
                    "breed",
                    "subspecies",
                    "animal",
                    "flybase",
                    "strain",
                ],
            },
            "caution": {
                "short_name": "-",
                "description": (
                    "Errors, inconsistencies, ambiguities regarding the "
                    "origin or other aspects of the cell line."
                ),
                "keywords": [
                    "caution",
                    "warning",
                    "error",
                    "inconsistency",
                    "ambiguity",
                ],
            },
            "cell": {
                "short_name": "cell-type",
                "description": ("Cell type from which the cell line is derived."),
                "keywords": ["cell type", "cell", "derived", "type"],
            },
            "char": {
                "short_name": "characteristics",
                "description": (
                    "Production process or specific biological properties of "
                    "the cell line."
                ),
                "keywords": [
                    "characteristics",
                    "properties",
                    "biological",
                    "production",
                    "process",
                    "cancer",
                    "tumor",
                    "malignant",
                ],
            },
            "donor": {
                "short_name": "donor-info",
                "description": (
                    "Miscellaneous information relevant to the donor of the cell line."
                ),
                "keywords": [
                    "donor",
                    "patient",
                    "miscellaneous",
                    "information",
                ],
            },
            "site": {
                "short_name": "derived-from-site",
                "description": (
                    "Body part (tissue or organ) the cell line is derived from."
                ),
                "keywords": [
                    "site",
                    "tissue",
                    "organ",
                    "body part",
                    "derived",
                    "lung",
                    "breast",
                    "colon",
                    "skin",
                    "blood",
                    "bone",
                    "brain",
                ],
            },
            "disc": {
                "short_name": "discontinued",
                "description": (
                    "Discontinuation status of the cell line in a cell line catalog."
                ),
                "keywords": [
                    "discontinued",
                    "unavailable",
                    "no longer available",
                    "status",
                ],
            },
            "time": {
                "short_name": "doubling-time",
                "description": "Population doubling-time of the cell line.",
                "keywords": [
                    "doubling time",
                    "doubling",
                    "population",
                    "time",
                    "hours",
                ],
            },
            "from": {
                "short_name": "-",
                "description": (
                    "Laboratory, research institute, university having "
                    "established the cell line."
                ),
                "keywords": [
                    "laboratory",
                    "lab",
                    "institute",
                    "university",
                    "established",
                ],
            },
            "group": {
                "short_name": "-",
                "description": (
                    "Specific group the cell line belongs to (example: fish "
                    "cell lines, vaccine production cell lines)."
                ),
                "keywords": [
                    "group",
                    "fish cell lines",
                    "vaccine production",
                    "stem cell",
                    "embryonic",
                ],
            },
            "kar": {
                "short_name": "karyotype",
                "description": (
                    "Information relevant to the chromosomes of a cell line "
                    "(often to describe chromosomal abnormalities)."
                ),
                "keywords": [
                    "karyotype",
                    "chromosome",
                    "chromosomal",
                    "abnormalities",
                    "defects",
                ],
            },
            "ko": {
                "short_name": "knockout",
                "description": (
                    "Gene(s) knocked-out in the cell line and method to obtain the KO."
                ),
                "keywords": ["knockout", "ko", "gene", "knocked-out"],
            },
            "msi": {
                "short_name": "-",
                "description": "Microsatellite instability degree.",
                "keywords": ["msi", "microsatellite instability"],
            },
            "misc": {
                "short_name": "miscellaneous",
                "description": "Miscellaneous remarks about the cell line.",
                "keywords": [
                    "miscellaneous",
                    "other",
                    "additional",
                    "notes",
                    "remarks",
                ],
            },
            "miss": {
                "short_name": "misspelling",
                "description": (
                    "Identified misspelling(s) of the cell line name with in "
                    "some case the specific publication or external resource "
                    "entry where it appears."
                ),
                "keywords": ["misspelling", "misspelled", "typo"],
            },
            "mabi": {
                "short_name": "mab-isotype",
                "description": (
                    "Monoclonal antibody isotype. Examples: IgG2a, kappa; IgM, lambda."
                ),
                "keywords": [
                    "isotype",
                    "igg",
                    "igm",
                    "iga",
                    "ige",
                    "monoclonal antibody",
                ],
            },
            "mabt": {
                "short_name": "mab-target",
                "description": (
                    "Monoclonal antibody target molecule. Generally a "
                    "specific protein or chemical compound."
                ),
                "keywords": [
                    "antibody",
                    "mab",
                    "target",
                    "targeting",
                    "protein",
                    "molecule",
                ],
            },
            "omics": {
                "short_name": "-",
                "description": ('"Omics" study(ies) carried out on the cell line.'),
                "keywords": [
                    "omics",
                    "genomics",
                    "transcriptomics",
                    "proteomics",
                    "metabolomics",
                    "study",
                ],
            },
            "part": {
                "short_name": "part-of",
                "description": (
                    "The cell line belongs to a specific panel or collection "
                    "of cell lines."
                ),
                "keywords": ["part", "panel", "collection", "belongs to"],
            },
            "pop": {
                "short_name": "population",
                "description": (
                    "Ethnic group, nationality of the individual from which "
                    "the cell line was sampled."
                ),
                "keywords": [
                    "population",
                    "ethnic",
                    "nationality",
                    "caucasian",
                    "african",
                    "asian",
                ],
            },
            "prob": {
                "short_name": "problematic",
                "description": (
                    "Known problem(s) related to the cell line: contaminated, "
                    "misidentified, misclassified cell line or appearing in a "
                    "retracted paper."
                ),
                "keywords": [
                    "problematic",
                    "contaminated",
                    "misidentified",
                    "problem",
                    "retracted",
                ],
            },
            "res": {
                "short_name": "resistance",
                "description": (
                    "Selected to be resistant to some chemical compound "
                    "(like a drug used in chemotherapy) or toxin. with a "
                    "cross-reference to either ChEBI, DrugBank, NCIt or "
                    "UniProtKB."
                ),
                "keywords": [
                    "resistance",
                    "resistant",
                    "drug",
                    "chemotherapy",
                    "toxin",
                    "cisplatin",
                    "doxorubicin",
                ],
            },
            "sen": {
                "short_name": "senescence",
                "description": "When a finite cell line will senesce.",
                "keywords": ["senescence", "senescent", "finite"],
            },
            "int": {
                "short_name": "integrated",
                "description": (
                    "Genetic element(s) integrated in the cell line: gene "
                    "name and identifier in CGNC, FlyBase, FPbase, HGNC, MGI, "
                    "RGD, UniProtKB, and VGNC."
                ),
                "keywords": ["integrated", "genetic element", "gene"],
            },
            "tfor": {
                "short_name": "transformant",
                "description": (
                    "What caused the cell line to be transformed: generally a "
                    "virus (with a cross-reference to NCBI taxon identifier), "
                    "a chemical compound (with a cross-reference to ChEBI) or "
                    "a form of irradiation (with a cross-reference to NCIt)."
                ),
                "keywords": [
                    "transformant",
                    "transformation",
                    "virus",
                    "chemical",
                    "irradiation",
                ],
            },
            "vir": {
                "short_name": "virology",
                "description": (
                    "Susceptibility of the cell line to viral infection, "
                    "presence of integrated viruses or any other "
                    "virology-related information."
                ),
                "keywords": [
                    "virology",
                    "viral",
                    "virus",
                    "susceptibility",
                    "infection",
                ],
            },
            "cc": {
                "short_name": "-",
                "description": (
                    "Comment(s). Any content described in fields "
                    "genome-ancestry, hla, registration, sequence-variation, "
                    "anecdotal, biotechnology, breed, caution, "
                    "characteristics, discontinued, donor-info, "
                    "doubling-time, from, group, karyotype, knockout, "
                    "miscellaneous, misspelling, mab-isotype, mab-target, "
                    "msi, omics, population, problematic, resistance, "
                    "senescence, transfected, transformant, virology."
                ),
                "keywords": ["comment", "note", "remark", "observation"],
            },
            "str": {
                "short_name": "-",
                "description": "Short tandem repeat profile.",
                "keywords": [
                    "str",
                    "short tandem repeat",
                    "microsatellite",
                    "profile",
                ],
            },
            "di": {
                "short_name": "-",
                "description": (
                    "Disease(s) suffered by the individual from which the "
                    "cell line originated with its NCI Thesaurus or ORDO "
                    "identifier."
                ),
                "keywords": [
                    "disease",
                    "condition",
                    "leukemia",
                    "lymphoma",
                    "carcinoma",
                    "sarcoma",
                ],
            },
            "din": {
                "short_name": "-",
                "description": (
                    "Disease(s) suffered by the individual from which the "
                    "cell line originated, restricted to diseases having a "
                    "NCI Thesaurus identifier."
                ),
                "keywords": ["disease", "nci", "thesaurus"],
            },
            "dio": {
                "short_name": "-",
                "description": (
                    "Disease(s) suffered by the individual from which the "
                    "cell line originated, restricted to diseases having an "
                    "ORDO identifier."
                ),
                "keywords": ["disease", "ordo"],
            },
            "ox": {
                "short_name": "-",
                "description": (
                    "Species of the individual from which the cell line "
                    "originates with its NCBI taxon identifier."
                ),
                "keywords": [
                    "species",
                    "organism",
                    "human",
                    "mouse",
                    "rat",
                    "ncbi",
                    "taxon",
                ],
            },
            "sx": {
                "short_name": "-",
                "description": (
                    "Sex of the individual from which the cell line originates."
                ),
                "keywords": [
                    "sex",
                    "gender",
                    "male",
                    "female",
                    "man",
                    "woman",
                ],
            },
            "ag": {
                "short_name": "-",
                "description": (
                    "Age at sampling time of the individual from which the "
                    "cell line was established."
                ),
                "keywords": [
                    "age",
                    "aged",
                    "years",
                    "months",
                    "days",
                    "sampling",
                ],
            },
            "oi": {
                "short_name": "-",
                "description": (
                    "Cell line(s) originating from same individual (sister cell lines)."
                ),
                "keywords": [
                    "sister",
                    "sibling",
                    "related",
                    "same individual",
                ],
            },
            "hi": {
                "short_name": "-",
                "description": (
                    "Parent cell line from which the cell line originates."
                ),
                "keywords": ["parent", "derived from"],
            },
            "ch": {
                "short_name": "-",
                "description": (
                    "Cell line(s) originated from the cell line (child cell lines)."
                ),
                "keywords": ["child", "derived", "subclone"],
            },
            "ca": {
                "short_name": "-",
                "description": (
                    "Category to which a cell line belongs, one of 14 defined "
                    "terms. Example: cancer cell line, hybridoma, transformed "
                    "cell line."
                ),
                "keywords": [
                    "category",
                    "cancer cell line",
                    "hybridoma",
                    "transformed",
                    "primary",
                    "immortalized",
                ],
            },
            "dt": {
                "short_name": "-",
                "description": (
                    "Creation date, last modification date and version number "
                    "of the cell line Cellosaurus entry."
                ),
                "keywords": ["date", "creation", "modification", "version"],
            },
            "dtc": {
                "short_name": "-",
                "description": ("Creation date of the cell line Cellosaurus entry."),
                "keywords": [
                    "created",
                    "creation",
                    "established",
                    "founded",
                ],
            },
            "dtu": {
                "short_name": "-",
                "description": (
                    "Last modification date of the cell line Cellosaurus entry."
                ),
                "keywords": [
                    "modified",
                    "modification",
                    "updated",
                    "changed",
                ],
            },
            "dtv": {
                "short_name": "-",
                "description": ("Version number of the cell line Cellosaurus entry."),
                "keywords": ["version", "v"],
            },
        }

        # Special species mappings with NCBI taxon IDs
        self.species_mappings = {
            "human": "ox:9606",
            "homo sapiens": "ox:9606",
            "mouse": "ox:10090",
            "mus musculus": "ox:10090",
            "rat": "ox:10116",
            "rattus norvegicus": "ox:10116",
        }

        # Boolean operator patterns
        self.boolean_patterns = [
            (r"\b(and|&)\b", " AND "),
            (r"\b(or|\|)\b", " OR "),
            (r"\b(not|!)\b", " NOT "),
        ]

        # Wildcard patterns
        self.wildcard_patterns = [
            (r"\*", "*"),
            (r"\?", "?"),
        ]

        # Range query patterns
        self.range_patterns = [
            (
                r"\b(\d+)\s*(?:to|-)\s*(\d+)\s*(hours?|days?|years?)\b",
                r"[\1 TO \2] \3",
            ),
            (
                r"\bbetween\s+(\d+)\s+and\s+(\d+)\s*(hours?|days?|years?)\b",
                r"[\1 TO \2] \3",
            ),
        ]

    def run(self, arguments):
        query = arguments.get("query")
        include_explanation = arguments.get("include_explanation", True)

        if not query:
            return {"status": "error", "error": "`query` parameter is required."}

        return self._convert_query(query, include_explanation)

    def _calculate_similarity(self, term: str, text: str) -> float:
        """
        Calculate similarity between a term and text using SequenceMatcher.
        """
        return SequenceMatcher(None, term.lower(), text.lower()).ratio()

    def _map_term_to_field(self, term: str) -> List[Tuple[str, float, str]]:
        """
        Map a natural language term to Cellosaurus fields based on semantic
        similarity.
        """
        matches = []
        term_lower = term.lower()

        # Direct field tag matches
        if term_lower in self.cellosaurus_fields:
            matches.append((term_lower, 1.0, "direct_field_tag"))

        # Species mappings
        if term_lower in self.species_mappings:
            field_tag = self.species_mappings[term_lower].split(":")[0]
            matches.append((field_tag, 1.0, "species_mapping"))

        # Keyword matching
        for field_tag, field_info in self.cellosaurus_fields.items():
            # Check keywords
            for keyword in field_info["keywords"]:
                if keyword.lower() in term_lower or term_lower in keyword.lower():
                    similarity = self._calculate_similarity(term, keyword)
                    matches.append((field_tag, similarity, "keyword_match:" + keyword))

            # Check description similarity
            desc_similarity = self._calculate_similarity(
                term, field_info["description"]
            )
            if desc_similarity > 0.3:  # Threshold for description matching
                matches.append((field_tag, desc_similarity, "description_match"))

            # Check short name similarity
            if field_info["short_name"] != "-":
                short_similarity = self._calculate_similarity(
                    term, field_info["short_name"]
                )
                if short_similarity > 0.3:
                    matches.append(
                        (
                            field_tag,
                            short_similarity,
                            "short_name_match:" + field_info["short_name"],
                        )
                    )

        # Sort by similarity score (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

    def _extract_field_terms(self, query: str) -> List[Tuple[str, str, float, str]]:
        """
        Extract field-specific terms from the query using semantic mapping.
        """
        terms = []
        query_lower = query.lower()

        # Split query into words and phrases
        words = re.findall(r"\b\w+\b", query_lower)

        # Also extract common phrases
        phrases = []
        for i in range(len(words) - 1):
            phrases.append(f"{words[i]} {words[i + 1]}")

        all_terms = words + phrases

        # Map each term to fields
        for term in all_terms:
            if len(term) < 2:  # Skip very short terms
                continue

            field_matches = self._map_term_to_field(term)

            # Take the best match if confidence is high enough
            if field_matches and field_matches[0][1] > 0.4:
                field_tag, confidence, reason = field_matches[0]

                # Handle special cases
                if field_tag == "ox" and term in self.species_mappings:
                    # Use the full species mapping (e.g., "ox:9606")
                    field_tag = self.species_mappings[term]
                    value = ""
                else:
                    value = term

                terms.append((field_tag, value, confidence, reason))

        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for field_tag, value, confidence, reason in terms:
            key = (field_tag, value.lower())
            if key not in seen:
                seen.add(key)
                unique_terms.append((field_tag, value, confidence, reason))

        return unique_terms

    def _apply_boolean_operators(self, query: str) -> str:
        """Convert natural language boolean operators to Solr syntax."""
        result = query
        for pattern, replacement in self.boolean_patterns:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result

    def _apply_range_queries(self, query: str) -> str:
        """Convert natural language ranges to Solr range syntax."""
        result = query
        for pattern, replacement in self.range_patterns:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result

    def _apply_wildcards(self, query: str) -> str:
        """Convert natural language wildcard patterns to Solr syntax."""
        result = query
        for pattern, replacement in self.wildcard_patterns:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result

    def _construct_solr_query(
        self, terms: List[Tuple[str, str, float, str]], original_query: str
    ) -> str:
        """Construct the final Solr query from extracted terms."""
        if not terms:
            # If no field-specific terms found, return original query as
            # general search
            return self._apply_boolean_operators(original_query.strip())

        # Build field-specific queries
        field_queries = []
        for field_tag, value, _confidence, _reason in terms:
            # Handle special field mappings that already include values
            # (like ox:9606)
            if ":" in field_tag and not value:
                field_queries.append(field_tag)
            elif ":" in field_tag and value:
                # Handle cases like "ox:9606" with additional value
                field_queries.append(
                    f"{field_tag} AND {field_tag.split(':')[0]}:{value}"
                )
            else:
                # Escape special characters in values
                escaped_value = re.sub(r'([+\-&|!(){}[\]^"~*?:\\/])', r"\\\1", value)
                field_queries.append(f"{field_tag}:{escaped_value}")

        # Join with AND by default (most restrictive)
        if len(field_queries) == 1:
            return field_queries[0]
        else:
            return f"({' AND '.join(field_queries)})"

    def _validate_solr_query(self, query: str) -> Tuple[bool, str]:
        """Basic validation of Solr query syntax."""
        try:
            # Check for balanced parentheses
            paren_count = query.count("(") - query.count(")")
            if paren_count != 0:
                return False, f"Unbalanced parentheses in query: {query}"

            # Check for balanced brackets in ranges
            bracket_count = query.count("[") - query.count("]")
            if bracket_count != 0:
                return False, f"Unbalanced brackets in range query: {query}"

            # Check for empty field queries
            if re.search(r":\s*$", query):
                return False, f"Empty field value in query: {query}"

            return True, "Valid Solr query"

        except Exception as e:
            return False, f"Query validation error: {str(e)}"

    def _convert_query(
        self, natural_query: str, include_explanation: bool = True
    ) -> Dict[str, Any]:
        """
        Convert natural language query to Solr syntax using systematic field
        mapping.
        """
        try:
            # Normalize input
            normalized_query = natural_query.lower()
            # Replace common conjunctions with spaces for better term
            # extraction
            normalized_query = re.sub(
                r"\b(with|from|in|of|for)\b", " ", normalized_query
            )
            # Remove extra whitespace
            normalized_query = re.sub(r"\s+", " ", normalized_query)

            # Apply transformations
            processed_query = self._apply_boolean_operators(normalized_query)
            processed_query = self._apply_range_queries(processed_query)
            processed_query = self._apply_wildcards(processed_query)

            # Extract field-specific terms using semantic mapping
            terms = self._extract_field_terms(natural_query)

            # Construct Solr query
            solr_query = self._construct_solr_query(terms, processed_query)

            # Validate the query
            is_valid, validation_msg = self._validate_solr_query(solr_query)

            result = {
                "success": True,
                "original_query": natural_query,
                "solr_query": solr_query,
                "is_valid": is_valid,
                "validation_message": validation_msg,
            }

            if include_explanation:
                result["explanation"] = {
                    "extracted_terms": [
                        {
                            "field": field_tag,
                            "value": value,
                            "confidence": confidence,
                            "match_reason": reason,
                        }
                        for field_tag, value, confidence, reason in terms
                    ],
                    "transformations_applied": [
                        "boolean_operators",
                        "range_queries",
                        "wildcards",
                    ],
                    "available_fields": list(self.cellosaurus_fields.keys()),
                }

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Query conversion failed: {e}",
                "original_query": natural_query,
            }


@register_tool("CellosaurusGetCellLineInfoTool")
class CellosaurusGetCellLineInfoTool(BaseTool):
    """
    Tool to get detailed information about a specific cell line using its
    accession number.
    """

    def __init__(self, tool_config, base_url="https://api.cellosaurus.org"):
        super().__init__(tool_config)
        self.base_url = base_url
        self.timeout_seconds = int(os.environ.get("CELLOSAURUS_TIMEOUT", "30"))

    def run(self, arguments):
        accession = arguments.get("accession")
        format_type = arguments.get("format", "json")
        fields = arguments.get("fields")

        if not accession:
            return {"status": "error", "error": "`accession` parameter is required."}

        return self._get_cell_line_info(accession, format_type, fields)

    def _get_cell_line_info(self, accession, format_type, fields):
        """Get detailed cell line information by accession number."""
        try:
            # Validate accession format
            # (Cellosaurus accessions start with CVCL_)
            if not accession.startswith("CVCL_"):
                return {
                    "status": "error",
                    "error": ("Accession must start with 'CVCL_' (Cellosaurus format)"),
                }

            # Validate format
            valid_formats = ["json", "xml", "txt", "fasta"]
            if format_type not in valid_formats:
                return {
                    "status": "error",
                    "error": (f"Format must be one of: {', '.join(valid_formats)}"),
                }

            # Validate fields if provided
            if fields is not None:
                if not isinstance(fields, list):
                    return {
                        "status": "error",
                        "error": "Fields must be a list of field names",
                    }

                # Valid Cellosaurus field tags
                valid_fields = {
                    "id",
                    "sy",
                    "idsy",
                    "ac",
                    "acas",
                    "dr",
                    "ref",
                    "rx",
                    "ra",
                    "rt",
                    "rl",
                    "ww",
                    "anc",
                    "hla",
                    "reg",
                    "var",
                    "anec",
                    "biot",
                    "breed",
                    "caution",
                    "cell",
                    "char",
                    "donor",
                    "site",
                    "disc",
                    "time",
                    "from",
                    "group",
                    "kar",
                    "ko",
                    "msi",
                    "misc",
                    "miss",
                    "mabi",
                    "mabt",
                    "omics",
                    "part",
                    "pop",
                    "prob",
                    "res",
                    "sen",
                    "int",
                    "tfor",
                    "vir",
                    "cc",
                    "str",
                    "di",
                    "din",
                    "dio",
                    "ox",
                    "sx",
                    "ag",
                    "oi",
                    "hi",
                    "ch",
                    "ca",
                    "dt",
                    "dtc",
                    "dtu",
                    "dtv",
                }

                invalid_fields = set(fields) - valid_fields
                if invalid_fields:
                    return {
                        "status": "error",
                        "error": f"Invalid fields: {list(invalid_fields)}",
                    }

            # Prepare request parameters
            params = {"format": format_type}
            if fields:
                params["fields"] = ",".join(fields)

            # Make API request
            url = f"{self.base_url}/cell-line/{accession}"
            headers = {"Accept": f"application/{format_type}"}

            resp = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()

            # Parse response based on format
            if format_type == "json":
                data = resp.json()

                # Extract cell line data from nested structure
                cell_line_data = None
                if isinstance(data, dict) and "Cellosaurus" in data:
                    cellosaurus_data = data["Cellosaurus"]
                    if (
                        "cell-line-list" in cellosaurus_data
                        and cellosaurus_data["cell-line-list"]
                    ):
                        cell_line_data = cellosaurus_data["cell-line-list"][0]

                if not cell_line_data:
                    return {
                        "status": "error",
                        "error": (f"No cell line data found for accession {accession}"),
                    }

                # Apply field filtering if requested
                if fields:
                    filtered_data = {}
                    for field in fields:
                        if field in cell_line_data:
                            filtered_data[field] = cell_line_data[field]
                    cell_line_data = filtered_data

                return {
                    "success": True,
                    "accession": accession,
                    "data": cell_line_data,
                    "format": format_type,
                }
            else:
                # For non-JSON formats, return the raw content
                return {
                    "success": True,
                    "accession": accession,
                    "data": resp.text,
                    "format": format_type,
                }

        except requests.HTTPError as http_err:
            status = getattr(http_err.response, "status_code", None)
            if status == 404:
                return {
                    "status": "error",
                    "error": f"Cell line with accession {accession} not found",
                }
            return {"status": "error", "error": f"HTTP {status}: {http_err}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
