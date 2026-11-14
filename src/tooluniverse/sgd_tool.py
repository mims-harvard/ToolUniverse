# sgd_tool.py
"""
SGD (Saccharomyces Genome Database) REST API tool for ToolUniverse.

SGD is the comprehensive resource for yeast (Saccharomyces cerevisiae)
genomics and molecular biology. It provides curated gene information,
phenotypes, GO annotations, genetic/physical interactions, and literature.

API: https://www.yeastgenome.org/backend
No authentication required. Free for academic/research use.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool


# A heavily studied gene can carry dozens of phenotypes per mutant type, so
# each bucket is capped and its full count reported.
PHENOTYPES_PER_MUTANT_TYPE = 25


def _sgd_id(link: Any) -> "str | None":
    """The SGD identifier out of a link: "/allele/S000278213" -> S000278213."""
    if not isinstance(link, str):
        return None
    for part in reversed(link.strip("/").split("/")):
        if part.upper().startswith("S") and part[1:].isdigit():
            return part
    return None


def _phenotype_terms(entries: Any) -> list:
    """One bucket of phenotype annotations, as terms with their SGD links."""
    out = []
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        if entry.get("display_name"):
            out.append(
                {"phenotype": entry.get("display_name"), "link": entry.get("link")}
            )
    return out


def _phenotype_summary(overview: Any) -> Dict[str, Any]:
    """The gene's phenotypes, by how the mutant was made.

    `experiment_categories`, which the tool already returned, counts assay
    kinds. This is what was observed: the classical annotations, and the
    large-scale ones bucketed by mutant type, which is what distinguishes a
    phenotype of losing the gene from one of over-expressing it.
    """
    if not isinstance(overview, dict):
        return {}
    classical = _phenotype_terms(overview.get("classical_phenotypes"))
    if isinstance(overview.get("classical_phenotypes"), dict):
        classical = []
        for entries in overview["classical_phenotypes"].values():
            classical.extend(_phenotype_terms(entries))
    large_scale = {}
    raw_large = overview.get("large_scale_phenotypes")
    if isinstance(raw_large, dict):
        for mutant_type, entries in raw_large.items():
            terms = _phenotype_terms(entries)
            if not terms:
                continue
            large_scale[mutant_type] = {
                "phenotypes": terms[:PHENOTYPES_PER_MUTANT_TYPE],
                "count": len(terms),
                "truncated": len(terms) > PHENOTYPES_PER_MUTANT_TYPE,
            }
    return {
        "paragraph": overview.get("paragraph"),
        "classical_phenotypes": classical[:PHENOTYPES_PER_MUTANT_TYPE],
        "classical_phenotype_count": len(classical),
        "classical_phenotypes_truncated": len(classical)
        > PHENOTYPES_PER_MUTANT_TYPE,
        "large_scale_phenotypes": large_scale,
        "strains": overview.get("strains") or [],
    }



def _go_accession(link: Any) -> "str | None":
    """The GO accession out of an SGD link: "/go/GO:0046540" -> "GO:0046540"."""
    if not isinstance(link, str):
        return None
    for part in reversed(link.strip("/").split("/")):
        if part.upper().startswith("GO:"):
            return part
    return None


SGD_BASE_URL = "https://www.yeastgenome.org/backend"


@register_tool("SGDTool")
class SGDTool(BaseTool):
    """
    Tool for querying the Saccharomyces Genome Database (SGD).

    SGD provides curated information about the budding yeast S. cerevisiae,
    including gene function, phenotypes, interactions, GO annotations,
    pathways, and literature.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get("endpoint_type", "locus")
        self.query_mode = tool_config.get("fields", {}).get("query_mode", "overview")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the SGD API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"SGD API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to SGD API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"SGD API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying SGD: {str(e)}",
            }

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint based on config."""
        if self.endpoint_type == "locus" and self.query_mode == "overview":
            return self._locus_overview(arguments)
        elif self.endpoint_type == "locus" and self.query_mode == "phenotype":
            return self._locus_phenotypes(arguments)
        elif self.endpoint_type == "locus" and self.query_mode == "go":
            return self._locus_go(arguments)
        elif self.endpoint_type == "locus" and self.query_mode == "interaction":
            return self._locus_interactions(arguments)
        elif self.endpoint_type == "locus" and self.query_mode == "regulation":
            return self._locus_regulation(arguments)
        elif self.endpoint_type == "locus" and self.query_mode == "sequence":
            return self._locus_sequence(arguments)
        elif self.endpoint_type == "locus" and self.query_mode == "disease":
            return self._locus_disease(arguments)
        elif self.endpoint_type == "search":
            return self._search(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type/query_mode: {self.endpoint_type}/{self.query_mode}",
            }

    @staticmethod
    def _paginate(
        items: list, arguments: Dict[str, Any], default_limit: int
    ) -> tuple[list, Dict[str, Any]]:
        limit = min(max(int(arguments.get("limit", default_limit)), 1), 1000)
        offset = max(int(arguments.get("offset", 0)), 0)
        page = items[offset : offset + limit]
        has_more = offset + len(page) < len(items)
        return page, {
            "total_results": len(items),
            "returned": len(page),
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
            "truncated": len(page) < len(items),
            "next_offset": offset + len(page) if has_more else None,
        }

    def _locus_overview(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get gene/locus overview from SGD by SGD ID."""
        sgd_id = arguments.get("sgd_id", "")
        if not sgd_id:
            return {
                "status": "error",
                "error": "sgd_id parameter is required (e.g., S000003219 or S000000259)",
            }

        url = f"{SGD_BASE_URL}/locus/{sgd_id}"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        raw = response.json()

        # SGD's aliases are not all the same kind of thing: alongside gene
        # synonyms the list holds "Protein version ID" (CAA84998.1),
        # "NCBI protein name" and others, each with its own source database.
        # Reducing every one to a bare display_name presented a GenBank
        # accession and a gene synonym as the same fact. `aliases` keeps the
        # names it always carried; `alias_details` says what each one is.
        raw_aliases = [a for a in raw.get("aliases", []) if isinstance(a, dict)]
        aliases = [a.get("display_name") for a in raw_aliases]
        alias_details = [
            {
                "name": a.get("display_name"),
                "category": a.get("category"),
                "source": (a.get("source") or {}).get("display_name"),
                "link": a.get("link"),
            }
            for a in raw_aliases
        ]
        alias_limit = min(max(int(arguments.get("alias_limit", 10)), 1), 1000)
        alias_offset = max(int(arguments.get("alias_offset", 0)), 0)
        alias_page = aliases[alias_offset : alias_offset + alias_limit]
        has_more_aliases = alias_offset + len(alias_page) < len(aliases)
        result = {
            "sgd_id": raw.get("sgdid"),
            "display_name": raw.get("display_name"),
            "gene_name": raw.get("gene_name"),
            "systematic_name": raw.get("format_name"),
            "locus_type": raw.get("locus_type"),
            "qualifier": raw.get("qualifier"),
            "description": raw.get("description"),
            "name_description": raw.get("name_description"),
            "uniprot_id": raw.get("uniprot_id"),
            "aliases": alias_page,
            "alias_details": alias_details[alias_offset : alias_offset + alias_limit],
            "qualities": raw.get("qualities", []),
            # SGD's own links out, grouped by what they are for. The record
            # carries 78 of them -- sequence resources, interaction databases,
            # protein localisation -- and the caller saw none.
            "resource_links": [
                {
                    "category": u.get("category"),
                    "name": u.get("display_name"),
                    "link": u.get("link"),
                }
                for u in (raw.get("urls") or [])
                if isinstance(u, dict)
            ],
            "paralogs": raw.get("paralogs") or [],
            "alleles": [
                a.get("display_name")
                for a in (raw.get("alleles") or [])
                if isinstance(a, dict) and a.get("display_name")
            ],
            # The same alleles with the SGD id out of `link_url`
            # ("/allele/S000278213"), which is how one is looked up. The name
            # list stays as it was.
            "allele_records": [
                {
                    "name": a.get("display_name"),
                    "sgd_id": _sgd_id(a.get("link_url")),
                    "link": a.get("link_url"),
                }
                for a in (raw.get("alleles") or [])
                if isinstance(a, dict) and a.get("display_name")
            ],
            "references_count": raw.get("references_count"),
            # SGD's own summaries of the gene, which are the fastest answer to
            # "what is known about this gene" and were dropped whole.
            # Both fields of this row used to carry the wrong thing. `go_id`
            # is SGD's internal numeric id (294137), not a GO accession, and
            # `slim_name` is the name of the SLIM SET -- "Yeast GO-Slim",
            # "Macromolecular complex terms" -- so every row read
            # `term: "Yeast GO-Slim"`. The term is `display_name`
            # ("U4/U6 x U5 tri-snRNP complex") and the GO accession is in
            # `link` ("/go/GO:0046540"). Two plausible names over two wrong
            # values is worse than the omission this replaced.
            "go_slim": [
                {
                    "term": entry.get("display_name"),
                    "go_id": _go_accession(entry.get("link")),
                    "slim_set": entry.get("slim_name"),
                    "sgd_internal_id": entry.get("go_id"),
                    "link": entry.get("link"),
                }
                for entry in ((raw.get("go_overview") or {}).get("go_slim") or [])
                if isinstance(entry, dict)
            ],
            "phenotype_experiment_categories": (
                raw.get("phenotype_overview") or {}
            ).get("experiment_categories")
            or [],
            # The phenotypes themselves. `experiment_categories` counts the
            # kinds of assay; "toxin resistance: increased" is the phenotype,
            # and SGD buckets the large-scale ones by mutant type -- null,
            # repressible, reduction of function, conditional -- which is what
            # says whether a phenotype follows from losing the gene or from
            # over-expressing it. All of it was dropped.
            "phenotype_summary": _phenotype_summary(raw.get("phenotype_overview")),
            "protein_overview": raw.get("protein_overview") or {},
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "SGD",
                "query": sgd_id,
                "endpoint": "locus/overview",
                "total_aliases": len(aliases),
                "aliases_returned": len(alias_page),
                "alias_limit": alias_limit,
                "alias_offset": alias_offset,
                "aliases_truncated": len(alias_page) < len(aliases),
                "has_more_aliases": has_more_aliases,
                "next_alias_offset": (
                    alias_offset + len(alias_page) if has_more_aliases else None
                ),
            },
        }

    def _locus_phenotypes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get phenotype annotations for a yeast gene."""
        sgd_id = arguments.get("sgd_id", "")
        if not sgd_id:
            return {"status": "error", "error": "sgd_id parameter is required"}

        url = f"{SGD_BASE_URL}/locus/{sgd_id}/phenotype_details"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        raw = response.json()

        raw_page, paging = self._paginate(raw, arguments, 50)
        results = []
        for p in raw_page:
            phenotype = p.get("phenotype", {})
            results.append(
                {
                    "phenotype": phenotype.get("display_name"),
                    "qualifier": phenotype.get("qualifier"),
                    "mutant_type": p.get("mutant_type"),
                    "experiment_type": p.get("experiment", {}).get("display_name")
                    if p.get("experiment")
                    else None,
                    # "classical genetics" or "large-scale survey": a
                    # phenotype from a targeted experiment and one from a
                    # genome-wide screen carry different weight.
                    "experiment_category": (p.get("experiment") or {}).get("category"),
                    "strain_name": p.get("strain", {}).get("display_name")
                    if p.get("strain")
                    else None,
                    "allele": p.get("allele", {}).get("display_name")
                    if p.get("allele")
                    else None,
                    "chemical": p.get("chemical", {}).get("display_name")
                    if p.get("chemical")
                    else None,
                    "reference": p.get("reference", {}).get("display_name")
                    if p.get("reference")
                    else None,
                    "reference_pubmed_id": (p.get("reference") or {}).get("pubmed_id"),
                    "reference_citation": (p.get("reference") or {}).get("citation"),
                    # THE MEASUREMENT behind the qualitative call. 25 of
                    # POL3's 65 annotations carry one: "Relative growth score:
                    # 0.0044" under `haploproficient`, "Relative fitness
                    # score: 1.000" under "competitive fitness: normal",
                    # "metascore strong (multiple hit)" under a chromosome
                    # instability call. The row reported the label alone.
                    "note": p.get("note"),
                    # And the experiment's own note, e.g. "mutants grown in
                    # 96-well microtiter plates".
                    "experiment_note": (p.get("experiment") or {}).get("note")
                    or p.get("experiment_details"),
                    # The experiment's own conditions. SGD lists these as
                    # `properties`, each with a class_type (chemical, allele,
                    # media), the item and the role it played -- which is the
                    # difference between a phenotype seen under a drug and one
                    # seen without it.
                    "experiment_properties": [
                        {
                            "class_type": prop.get("class_type"),
                            "role": prop.get("role"),
                            "name": (prop.get("bioitem") or {}).get("display_name")
                            or (prop.get("bioentity") or {}).get("display_name")
                            or prop.get("note"),
                            "value": prop.get("concentration") or prop.get("value"),
                            "unit": prop.get("unit"),
                        }
                        for prop in (p.get("properties") or [])
                        if isinstance(prop, dict)
                    ],
                    "details": p.get("details"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "SGD",
                **paging,
                "query": sgd_id,
                "endpoint": "locus/phenotype_details",
            },
        }

    def _locus_go(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get Gene Ontology annotations for a yeast gene."""
        sgd_id = arguments.get("sgd_id", "")
        if not sgd_id:
            return {"status": "error", "error": "sgd_id parameter is required"}

        url = f"{SGD_BASE_URL}/locus/{sgd_id}/go_details"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        raw = response.json()

        raw_page, paging = self._paginate(raw, arguments, 50)
        results = []
        for g in raw_page:
            go = g.get("go", {})
            results.append(
                {
                    "go_id": go.get("go_id"),
                    "go_term": go.get("display_name"),
                    "go_aspect": g.get("go_aspect"),
                    "qualifier": g.get("qualifier"),
                    "evidence_code": g.get("evidence_code"),
                    "annotation_type": g.get("annotation_type"),
                    "source": g.get("source", {}).get("display_name")
                    if g.get("source")
                    else None,
                    "reference": g.get("reference", {}).get("display_name")
                    if g.get("reference")
                    else None,
                    # The PMID. A GO annotation with an evidence code and no
                    # resolvable reference cannot be checked against the paper
                    # the code refers to.
                    "reference_pubmed_id": (g.get("reference") or {}).get("pubmed_id"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "SGD",
                **paging,
                "query": sgd_id,
                "endpoint": "locus/go_details",
            },
        }

    def _locus_interactions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get genetic and physical interactions for a yeast gene."""
        sgd_id = arguments.get("sgd_id", "")
        if not sgd_id:
            return {"status": "error", "error": "sgd_id parameter is required"}

        url = f"{SGD_BASE_URL}/locus/{sgd_id}/interaction_details"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        raw = response.json()

        raw_page, paging = self._paginate(raw, arguments, 50)
        results = []
        for i in raw_page:
            locus1 = i.get("locus1", {})
            locus2 = i.get("locus2", {})
            # SGD states the direction in `bait_hit`, and it is not always
            # "Bait-Hit": on S000003219's 180 interactions, 83 are "Hit-Bait",
            # meaning locus1 is the HIT. Labelling locus1 the bait
            # unconditionally reported the roles backwards on 46% of rows,
            # which for a two-hybrid result inverts which protein was the
            # probe. Read the direction instead of assuming it.
            bait_hit = i.get("bait_hit") or ""
            if bait_hit.strip().lower().startswith("hit"):
                bait, hit = locus2, locus1
            else:
                bait, hit = locus1, locus2
            reference = i.get("reference") or {}
            results.append(
                {
                    "interaction_type": i.get("interaction_type"),
                    # Was `i.get("experiment_type")`, a key the API does not
                    # send, so this was null on every row ever returned. The
                    # experiment is under `experiment.display_name`:
                    # "Two-hybrid", "Affinity Capture-MS".
                    "experiment_type": (i.get("experiment") or {}).get("display_name"),
                    "bait_hit": i.get("bait_hit"),
                    "bait_gene": bait.get("display_name"),
                    "hit_gene": hit.get("display_name"),
                    "bait_sgdid": self._sgdid_from_link(bait.get("link")),
                    "hit_sgdid": self._sgdid_from_link(hit.get("link")),
                    "bait_systematic_name": bait.get("format_name"),
                    "hit_systematic_name": hit.get("format_name"),
                    "annotation_type": i.get("annotation_type"),
                    # What was actually observed. A genetic interaction's
                    # phenotype and the allele's mutant type are the result;
                    # without them the row says only that a pair interacts.
                    "phenotype": i.get("phenotype"),
                    "mutant_type": i.get("mutant_type"),
                    "modification": i.get("modification"),
                    "note": i.get("note"),
                    "source": (i.get("source") or {}).get("display_name"),
                    "reference": reference.get("display_name"),
                    "reference_pubmed_id": reference.get("pubmed_id"),
                    "reference_sgdid": self._sgdid_from_link(reference.get("link")),
                    # Which alleles were crossed, and how strong the
                    # interaction was. SGD reports an SGA score and its
                    # p-value per allele pair -- the quantitative result of the
                    # experiment -- and the row carried neither, so a genetic
                    # interaction arrived with no measure of its strength.
                    "alleles": [
                        {
                            "allele1": a.get("allele1_name"),
                            "allele2": a.get("allele2_name"),
                            "sga_score": a.get("sga_score"),
                            "p_value": a.get("pvalue"),
                        }
                        for a in (i.get("alleles") or [])
                        if isinstance(a, dict)
                    ],
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "SGD",
                **paging,
                "query": sgd_id,
                "endpoint": "locus/interaction_details",
            },
        }

    @staticmethod
    def _sgdid_from_link(link: str) -> str:
        """Extract the SGD identifier (S0000...) from a '/locus/S000...' link."""
        return link.split("/")[-1] if link else None

    def _locus_regulation(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get transcriptional regulation network (regulator<->target pairs)."""
        sgd_id = arguments.get("sgd_id", "")
        if not sgd_id:
            return {
                "status": "error",
                "error": "sgd_id parameter is required (e.g., S000000364 for CDC28)",
            }

        url = f"{SGD_BASE_URL}/locus/{sgd_id}/regulation_details"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        raw = response.json() or []

        raw_page, paging = self._paginate(raw, arguments, 100)
        results = []
        for r in raw_page:
            locus1 = r.get("locus1") or {}
            locus2 = r.get("locus2") or {}
            evidence = r.get("evidence") or {}
            reference = r.get("reference") or {}
            results.append(
                {
                    "regulator": locus1.get("display_name"),
                    "regulator_sgdid": self._sgdid_from_link(locus1.get("link")),
                    "target": locus2.get("display_name"),
                    "target_sgdid": self._sgdid_from_link(locus2.get("link")),
                    "regulation_of": r.get("regulation_of"),
                    "direction": r.get("direction"),
                    "happens_during": r.get("happens_during"),
                    "evidence": evidence.get("display_name"),
                    "annotation_type": r.get("annotation_type"),
                    "reference": reference.get("display_name"),
                    "pubmed_id": reference.get("pubmed_id"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "SGD",
                **paging,
                "query": sgd_id,
                "endpoint": "locus/regulation_details",
            },
        }

    def _locus_sequence(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get genomic/coding/protein sequence and coordinates for a yeast gene."""
        sgd_id = arguments.get("sgd_id", "")
        if not sgd_id:
            return {
                "status": "error",
                "error": "sgd_id parameter is required (e.g., S000000364 for CDC28)",
            }

        url = f"{SGD_BASE_URL}/locus/{sgd_id}/sequence_details"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        raw = response.json() or {}

        def _first_block(entries):
            """The reference (S288C) sequence block, falling back to the first.

            SGD answers one block per sequenced strain. Which strain the
            returned coordinates and residues belong to was never stated, and
            when S288C is absent the fallback silently hands back a different
            strain's sequence under the same field names -- so a caller
            comparing positions to the reference genome could be comparing
            against another isolate without any sign of it.
            """
            if not isinstance(entries, list) or not entries:
                return {}, None, 0
            for e in entries:
                strain = e.get("strain") or {}
                if "S288C" in (strain.get("display_name") or ""):
                    return e, True, len(entries)
            return entries[0], False, len(entries)

        def _provenance(block):
            strain = block.get("strain") or {}
            contig = block.get("contig") or {}
            return {
                "strain": strain.get("display_name"),
                "contig": contig.get("display_name"),
                "contig_systematic_name": contig.get("format_name"),
            }

        genomic, genomic_is_reference, genomic_strains = _first_block(
            raw.get("genomic_dna")
        )
        coding, coding_is_reference, coding_strains = _first_block(
            raw.get("coding_dna")
        )
        protein, protein_is_reference, protein_strains = _first_block(
            raw.get("protein")
        )

        result = {
            "sgd_id": sgd_id,
            "genomic_dna": {
                "start": genomic.get("start"),
                "end": genomic.get("end"),
                "strand": genomic.get("strand"),
                "length": len(genomic.get("residues") or ""),
                "residues": genomic.get("residues"),
                **_provenance(genomic),
                "is_reference_strain": genomic_is_reference,
                "strains_available": genomic_strains,
            },
            "coding_dna": {
                "length": len(coding.get("residues") or ""),
                "residues": coding.get("residues"),
                **_provenance(coding),
                "is_reference_strain": coding_is_reference,
                "strains_available": coding_strains,
            },
            "protein": {
                "length": len(protein.get("residues") or ""),
                "residues": protein.get("residues"),
                **_provenance(protein),
                "is_reference_strain": protein_is_reference,
                "strains_available": protein_strains,
            },
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "SGD",
                "query": sgd_id,
                "endpoint": "locus/sequence_details",
            },
        }

    def _locus_disease(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get curated gene-disease (DOID) associations for a yeast gene."""
        sgd_id = arguments.get("sgd_id", "")
        if not sgd_id:
            return {
                "status": "error",
                "error": "sgd_id parameter is required (e.g., S000000364 for CDC28)",
            }

        url = f"{SGD_BASE_URL}/locus/{sgd_id}/disease_details"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        raw = response.json() or []

        raw_page, paging = self._paginate(raw, arguments, 50)
        results = []
        for r in raw_page:
            disease = r.get("disease") or {}
            locus = r.get("locus") or {}
            reference = r.get("reference") or {}
            source = r.get("source") or {}
            results.append(
                {
                    "disease_name": disease.get("display_name"),
                    "disease_id": disease.get("disease_id"),
                    "annotation_type": r.get("annotation_type"),
                    "qualifier": r.get("qualifier"),
                    "locus": locus.get("display_name"),
                    "locus_sgdid": self._sgdid_from_link(locus.get("link")),
                    "source": source.get("display_name"),
                    "reference": reference.get("display_name"),
                    "pubmed_id": reference.get("pubmed_id"),
                    "evidence_code": (r.get("evidence_code") or {}).get("display_name"),
                    "experiment_type": (r.get("experiment") or {}).get("display_name"),
                    # The same experiment-properties shape the phenotype rows
                    # carry: which allele or construct, and the role it played.
                    "experiment_properties": [
                        {
                            "class_type": prop.get("class_type"),
                            "role": prop.get("role"),
                            "name": (prop.get("bioentity") or {}).get("display_name")
                            or (prop.get("bioitem") or {}).get("display_name")
                            or prop.get("note"),
                        }
                        for prop in (r.get("properties") or [])
                        if isinstance(prop, dict)
                    ],
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "SGD",
                **paging,
                "query": sgd_id,
                "endpoint": "locus/disease_details",
            },
        }

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search SGD for genes, GO terms, phenotypes, etc."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        limit = min(arguments.get("limit", 10), 50)
        offset = arguments.get("offset", 0)
        category = arguments.get("category", "")

        # The endpoint reads ``q``; a ``query`` parameter is ignored and the call
        # then lists all 348k records (every category) whatever the text was.
        params = {
            "q": query,
            "limit": limit,
            "offset": offset,
        }
        if category:
            params["category"] = category

        url = f"{SGD_BASE_URL}/get_search_results"
        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        if raw is None:
            return {
                "status": "success",
                "data": [],
                "metadata": {"total_results": 0, "query": query, "source": "SGD"},
            }

        results = []
        for r in raw.get("results", []):
            description = r.get("description") or ""
            results.append(
                {
                    "name": r.get("name"),
                    "category": r.get("category"),
                    "description": description,
                    "description_length": len(description),
                    "href": r.get("href"),
                    "aliases": r.get("aliases"),
                    # "Active", "Uncharacterized", "Dubious": whether the hit
                    # is a gene SGD still stands behind.
                    "status": r.get("status"),
                    "bioentity_id": r.get("bioentity_id"),
                }
            )

        # Extract aggregation info
        categories = {}
        for agg in raw.get("aggregations", []):
            if agg.get("key") == "category":
                for v in agg.get("values", []):
                    categories[v["key"]] = v["total"]

        total = raw.get("total", {})
        total_results = (
            total.get("value", len(results))
            if isinstance(total, dict)
            else int(total or len(results))
        )
        has_more = offset + len(results) < total_results

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "total_results": total_results,
                "categories": categories,
                "query": query,
                "offset": offset,
                "limit": limit,
                "returned": len(results),
                "has_more": has_more,
                "next_offset": offset + len(results) if has_more else None,
                "source": "SGD",
                "endpoint": "search",
            },
        }
