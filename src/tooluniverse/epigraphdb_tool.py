"""
EpiGraphDB API tool for ToolUniverse.

EpiGraphDB is a database and analysis platform integrating epidemiological data
with knowledge graph approaches. It provides Mendelian Randomization analysis,
genetic correlations, drug repurposing insights, and GWAS-to-disease ontology mappings.

API: https://api.epigraphdb.org
No authentication required. Public access.

Documentation: https://epigraphdb.org
"""

import requests
from typing import Any

from .base_rest_tool import BaseRESTTool
from .tool_registry import register_tool

EPIGRAPHDB_BASE = "https://api.epigraphdb.org"


@register_tool("EpiGraphDBTool")
class EpiGraphDBTool(BaseRESTTool):
    """
    Tool for querying the EpiGraphDB API.

    Provides access to:
    - Mendelian Randomization (MR) results between GWAS traits
    - Genetic correlations between traits
    - Drug repurposing via genetic evidence (drugs targeting risk factor genes)
    - GWAS trait to EFO/disease ontology mapping
    - Gene druggability information via PPI network
    - Gene-drug associations from pharmacogenomics databases
    - OpenGWAS GWAS study search

    Uses IEU OpenGWAS trait IDs (e.g., 'ieu-a-2' for BMI, 'ieu-a-7' for CHD).
    No authentication required.
    """

    def __init__(self, tool_config: dict):
        super().__init__(tool_config)
        self.timeout = 45  # MR queries can be slow
        self.operation = tool_config.get("fields", {}).get("operation", "mr")

    def run(self, arguments: dict) -> dict:
        """Execute the EpiGraphDB API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"EpiGraphDB request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to EpiGraphDB. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"EpiGraphDB HTTP error: {e.response.status_code} - {e.response.text[:200]}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying EpiGraphDB: {str(e)}",
            }

    def _query(self, arguments: dict) -> dict:
        """Route to the appropriate endpoint."""
        op = self.operation
        if op == "mr":
            return self._get_mr(arguments)
        elif op == "genetic_cor":
            return self._get_genetic_cor(arguments)
        elif op == "drugs_risk_factors":
            return self._get_drugs_risk_factors(arguments)
        elif op == "gwas_efo":
            return self._get_gwas_efo(arguments)
        elif op == "disease_efo":
            return self._get_disease_efo(arguments)
        elif op == "gene_search":
            return self._search_gene(arguments)
        elif op == "gene_drugs":
            return self._get_gene_drugs(arguments)
        elif op == "opengwas_search":
            return self._search_opengwas(arguments)
        elif op == "literature_evidence":
            return self._get_literature_evidence(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {op}"}

    @staticmethod
    def _split_triple(name: str, predicate: str) -> tuple:
        """Split a SemMedDB triple 'name' into (subject, object).

        EpiGraphDB returns the triple as a single string like
        'troglitazone INHIBITS Leptin|LEP' plus a separate 'predicate' field.
        Split on the predicate token (surrounded by spaces) to recover the
        subject and object. Fall back to (name, None) when the split fails.
        """
        if predicate and name:
            sep = f" {predicate} "
            if sep in name:
                subject, _, obj = name.partition(sep)
                return subject.strip(), obj.strip()
        return name, None

    def _get_literature_evidence(self, arguments: dict) -> dict:
        """Get SemMedDB literature triple evidence supporting a GWAS trait.

        Surfaces the literature/support-path evidence (SemMedDB
        subject-predicate-object triples linked to a GWAS trait via mined
        PubMed articles), complementing the MR/gene-drug evidence paths.
        """
        trait = arguments.get("trait", "").strip()
        if not trait:
            return {
                "status": "error",
                "error": "trait parameter is required (e.g., 'body mass index')",
            }

        pval_threshold = float(arguments.get("pval_threshold", 1e-8))
        params = {"trait": trait, "pval_threshold": pval_threshold}
        resp = requests.get(
            f"{EPIGRAPHDB_BASE}/literature/gwas",
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])

        rows = []
        for r in results[:100]:
            triple = r.get("triple", {})
            gwas = r.get("gwas", {})
            lit = r.get("lit", {})
            predicate = triple.get("predicate")
            subject, obj = self._split_triple(triple.get("name", ""), predicate)
            rows.append(
                {
                    "triple_subject": subject,
                    "triple_predicate": predicate,
                    "triple_object": obj,
                    "pubmed_id": lit.get("id"),
                    "gwas_trait": gwas.get("trait"),
                }
            )

        metadata = {
            "trait": trait,
            "pval_threshold": pval_threshold,
            "source": "EpiGraphDB / SemMedDB",
            "description": (
                "SemMedDB literature triples (subject-predicate-object) mined "
                "from PubMed and linked to GWAS hits for the trait. Each row "
                "cites a supporting article (pubmed_id). This is the "
                "literature/support-path evidence, complementing MR and "
                "gene-drug evidence."
            ),
        }
        if not results:
            metadata["note"] = (
                f"No SemMedDB literature triples for '{trait}' at "
                f"pval_threshold={pval_threshold}. The trait is matched "
                "case-insensitively as a substring of GWAS labels; try a "
                "broader trait name or a less stringent pval_threshold."
            )

        return {
            "status": "success",
            "data": {
                "literature_triples": rows,
                "total_count": len(results),
            },
            "metadata": metadata,
        }

    @staticmethod
    def _casing_variants(trait: str) -> list:
        """Return trait label casing variants to try, original first.

        EpiGraphDB's /mr endpoint matches GWAS trait labels exactly and
        case-sensitively (e.g. 'coronary heart disease' returns nothing but
        'Coronary heart disease' returns results). Try the sentence-case form
        as a fallback so a lowercase input does not silently miss.
        """
        variants = [trait]
        for variant in (trait.capitalize(), trait.title()):
            if variant not in variants:
                variants.append(variant)
        return variants

    def _query_mr(self, exposure: str, outcome: str, pval_threshold: float) -> list:
        """Call the EpiGraphDB /mr endpoint for one exposure/outcome label pair."""
        params = {
            "exposure_trait": exposure,
            "outcome_trait": outcome,
            "pval_threshold": pval_threshold,
            "mode": "table",
        }
        resp = requests.get(
            f"{EPIGRAPHDB_BASE}/mr", params=params, timeout=self.timeout
        )
        resp.raise_for_status()
        return resp.json().get("results", [])

    def _get_mr(self, arguments: dict) -> dict:
        """Get Mendelian Randomization results between exposure and outcome traits."""
        exposure_trait = arguments.get("exposure_trait", "").strip()
        outcome_trait = arguments.get("outcome_trait", "").strip()
        if not exposure_trait or not outcome_trait:
            return {
                "status": "error",
                "error": "Both exposure_trait and outcome_trait are required",
            }

        pval_threshold = float(arguments.get("pval_threshold", 1e-5))

        results = self._query_mr(exposure_trait, outcome_trait, pval_threshold)
        used_exposure, used_outcome = exposure_trait, outcome_trait

        # Fallback: EpiGraphDB trait labels are case-sensitive, so retry with
        # sentence-case variants when the exact labels return nothing.
        if not results:
            for ex in self._casing_variants(exposure_trait):
                for out in self._casing_variants(outcome_trait):
                    if (ex, out) == (exposure_trait, outcome_trait):
                        continue  # already tried the exact labels above
                    retry = self._query_mr(ex, out, pval_threshold)
                    if retry:
                        results, used_exposure, used_outcome = retry, ex, out
                        break
                if results:
                    break

        mr_results = []
        for r in results[:50]:
            exposure = r.get("exposure", {})
            outcome = r.get("outcome", {})
            mr = r.get("mr", {})
            mr_results.append(
                {
                    "exposure_id": exposure.get("id"),
                    "exposure_trait": exposure.get("trait"),
                    "outcome_id": outcome.get("id"),
                    "outcome_trait": outcome.get("trait"),
                    "beta": mr.get("b"),
                    "se": mr.get("se"),
                    "pval": mr.get("pval"),
                    "method": mr.get("method"),
                    "selection": mr.get("selection"),
                    "moescore": mr.get("moescore"),
                }
            )

        metadata = {
            "exposure_trait": used_exposure,
            "outcome_trait": used_outcome,
            "pval_threshold": pval_threshold,
            "source": "EpiGraphDB",
            "description": (
                "Mendelian Randomization evidence. beta = causal effect estimate. "
                "moescore > 0.9 suggests high-quality instruments."
            ),
        }
        if not results:
            # Don't let an exact-label miss read as 'no causal evidence'.
            metadata["note"] = (
                f"No MR results for exposure '{exposure_trait}' -> outcome "
                f"'{outcome_trait}'. EpiGraphDB matches exact, case-sensitive GWAS "
                "trait labels. Use EpiGraphDB_search_opengwas to find the exact "
                "trait label, then retry with that label."
            )
        elif (used_exposure, used_outcome) != (exposure_trait, outcome_trait):
            metadata["note"] = (
                f"Input labels did not match exactly; matched on '{used_exposure}'"
                f" -> '{used_outcome}' after case normalization."
            )

        return {
            "status": "success",
            "data": {
                "mr_results": mr_results,
                "total_count": len(results),
            },
            "metadata": metadata,
        }

    def _get_genetic_cor(self, arguments: dict) -> dict:
        """Get genetic correlations between a trait and other GWAS traits."""
        trait = arguments.get("trait", "").strip()
        if not trait:
            return {
                "status": "error",
                "error": "trait parameter is required (e.g., 'Body mass index')",
            }

        # NOTE: the /genetic-cor endpoint ignores pval_threshold (it returns a
        # fixed |rg| > 0.8 set), so it is intentionally not forwarded.
        results = self._query_genetic_cor(trait)
        used_trait = trait
        # The /genetic-cor graph matches exact, case-sensitive trait labels;
        # retry sentence-case variants when the exact label returns nothing.
        if not results:
            for variant in self._casing_variants(trait):
                if variant == trait:
                    continue
                retry = self._query_genetic_cor(variant)
                if retry:
                    results, used_trait = retry, variant
                    break

        cor_results = []
        for r in results[:50]:
            trait1 = r.get("trait1", {})
            trait2 = r.get("trait2", {})
            cor = r.get("cor", {})
            cor_results.append(
                {
                    "trait1_id": trait1.get("id"),
                    "trait1_trait": trait1.get("trait"),
                    "trait2_id": trait2.get("id"),
                    "trait2_trait": trait2.get("trait"),
                    "rg": cor.get("rg"),
                    "rg_se": cor.get("rg_se"),
                    "rg_pval": cor.get("rg_pval"),
                    "h2": cor.get("h2"),
                    "h2_intercept": cor.get("h2_intercept"),
                }
            )

        metadata = {
            "trait": used_trait,
            "source": "EpiGraphDB",
            "description": (
                "rg = genetic correlation coefficient (-1 to 1). The /genetic-cor "
                "endpoint returns only strong correlations (|rg| > 0.8); the "
                "pval_threshold argument is not applied by the upstream API."
            ),
        }
        if not results:
            # Many common labels (e.g. 'Body mass index') have no node in the
            # genetic-correlation graph even though they exist in OpenGWAS;
            # don't let that read as 'no shared genetics'.
            metadata["note"] = (
                f"No genetic correlations found for '{trait}'. The /genetic-cor "
                "graph matches exact, case-sensitive labels and only stores "
                "|rg| > 0.8 edges, so many traits return empty. Try a related "
                "label (e.g. 'Waist circumference' for adiposity) or rely on "
                "bidirectional MR for triangulation instead."
            )
        elif used_trait != trait:
            metadata["note"] = (
                f"Matched on '{used_trait}' after case normalization of '{trait}'."
            )

        return {
            "status": "success",
            "data": {
                "correlations": cor_results,
                "total_count": len(results),
            },
            "metadata": metadata,
        }

    def _query_genetic_cor(self, trait: str) -> list:
        """Call the EpiGraphDB /genetic-cor endpoint for one trait label."""
        params = {"trait": trait, "mode": "table"}
        resp = requests.get(
            f"{EPIGRAPHDB_BASE}/genetic-cor", params=params, timeout=self.timeout
        )
        resp.raise_for_status()
        return resp.json().get("results", [])

    def _get_drugs_risk_factors(self, arguments: dict) -> dict:
        """Get drugs associated with a risk factor trait via genetic evidence."""
        trait = arguments.get("trait", "").strip()
        if not trait:
            return {
                "status": "error",
                "error": "trait parameter is required (e.g., 'Body mass index', 'LDL cholesterol')",
            }

        pval_threshold = float(arguments.get("pval_threshold", 1e-4))
        params = {
            "trait": trait,
            "pval_threshold": pval_threshold,
            "mode": "table",
        }

        url = f"{EPIGRAPHDB_BASE}/drugs/risk-factors"
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])

        # Deduplicate by drug label
        seen_drugs: dict[str, Any] = {}
        for r in results:
            drug = r.get("drug", {})
            drug_label = drug.get("label", "")
            gene = r.get("gene", {})
            variant = r.get("variant", {})

            if drug_label not in seen_drugs:
                seen_drugs[drug_label] = {
                    "drug": drug_label,
                    "gene": gene.get("name"),
                    "variant": variant.get("name"),
                    "evidence_count": 1,
                }
            else:
                seen_drugs[drug_label]["evidence_count"] += 1

        drug_list = sorted(seen_drugs.values(), key=lambda x: -x["evidence_count"])[:30]

        return {
            "status": "success",
            "data": {
                "drugs": drug_list,
                "total_evidence_count": len(results),
                "unique_drug_count": len(seen_drugs),
            },
            "metadata": {
                "trait": trait,
                "pval_threshold": pval_threshold,
                "source": "EpiGraphDB",
                "description": (
                    "Drugs whose target genes are associated with the trait via GWAS. "
                    "Useful for drug repurposing and prioritization."
                ),
            },
        }

    def _get_gwas_efo(self, arguments: dict) -> dict:
        """Map GWAS traits to EFO (Experimental Factor Ontology) terms."""
        trait = arguments.get("trait", "").strip()
        if not trait:
            return {
                "status": "error",
                "error": "trait parameter is required (e.g., 'Body mass index', 'coronary artery disease')",
            }

        params = {
            "trait": trait,
            "mode": "table",
        }

        url = f"{EPIGRAPHDB_BASE}/ontology/gwas-efo"
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])

        # Deduplicate by EFO term
        seen_efo: dict = {}
        for r in results:
            efo = r.get("efo", {})
            gwas = r.get("gwas", {})
            efo_id = efo.get("id", "")
            if efo_id not in seen_efo:
                seen_efo[efo_id] = {
                    "efo_id": efo_id,
                    "efo_label": efo.get("value"),
                    "gwas_id": gwas.get("id"),
                    "gwas_trait": gwas.get("trait"),
                    "score": r.get("r", {}).get("score"),
                }

        efo_list = list(seen_efo.values())

        return {
            "status": "success",
            "data": {
                "efo_mappings": efo_list,
                "total_count": len(efo_list),
            },
            "metadata": {
                "trait": trait,
                "source": "EpiGraphDB",
                "description": "Maps GWAS trait names to EFO ontology terms for standardization",
            },
        }

    def _get_disease_efo(self, arguments: dict) -> dict:
        """Map a disease label to EFO terms and associated GWAS studies."""
        disease = arguments.get("disease", "").strip()
        if not disease:
            return {
                "status": "error",
                "error": "disease parameter is required (e.g., 'type 2 diabetes', 'breast cancer')",
            }

        params = {
            "disease_label": disease,
            "mode": "table",
        }

        url = f"{EPIGRAPHDB_BASE}/ontology/disease-efo"
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])
        mappings = []
        for r in results[:20]:
            efo = r.get("efo", {})
            gwas = r.get("gwas", {})
            mappings.append(
                {
                    "efo_id": efo.get("id"),
                    "efo_label": efo.get("value"),
                    "gwas_id": gwas.get("id"),
                    "gwas_trait": gwas.get("trait"),
                    "score": r.get("r", {}).get("score"),
                }
            )

        return {
            "status": "success",
            "data": {
                "disease_efo_mappings": mappings,
                "total_count": len(results),
            },
            "metadata": {
                "disease": disease,
                "source": "EpiGraphDB",
                "description": "Maps disease labels to EFO terms and OpenGWAS studies",
            },
        }

    def _search_gene(self, arguments: dict) -> dict:
        """Search for genes in EpiGraphDB by name or Ensembl ID."""
        gene_name = arguments.get("gene_name")
        gene_id = arguments.get("gene_id")

        if not gene_name and not gene_id:
            return {
                "status": "error",
                "error": "Either gene_name or gene_id (Ensembl ID) is required",
            }

        params: dict[str, Any] = {"limit": min(int(arguments.get("limit", 10)), 50)}
        if gene_name:
            params["name"] = gene_name
        elif gene_id:
            params["id"] = gene_id

        url = f"{EPIGRAPHDB_BASE}/meta/nodes/Gene/search"
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])
        genes = []
        for r in results:
            node = r.get("node", {})
            genes.append(
                {
                    "ensembl_id": node.get("ensembl_id"),
                    "name": node.get("_name"),
                    "description": node.get("description"),
                    "chr": node.get("chr"),
                    "start": node.get("start"),
                    "end": node.get("end"),
                    "gene_type": node.get("type"),
                    "druggability_tier": node.get("druggability_tier"),
                    "bio_druggable": node.get("bio_druggable"),
                    "small_mol_druggable": node.get("small_mol_druggable"),
                }
            )

        return {
            "status": "success",
            "data": {
                "genes": genes,
                "total_found": len(genes),
            },
            "metadata": {
                "query_name": gene_name,
                "query_id": gene_id,
                "source": "EpiGraphDB",
                "description": "Gene info including druggability tiers from EpiGraphDB",
            },
        }

    def _get_gene_drugs(self, arguments: dict) -> dict:
        """Get drug-gene associations from pharmacogenomics databases."""
        gene_name = (
            arguments.get("gene_name") or arguments.get("gene_symbol") or ""
        ).strip()
        if not gene_name:
            return {
                "status": "error",
                "error": "gene_name parameter is required (e.g., 'TP53', 'BRCA1', 'EGFR')",
            }

        params = {
            "gene_name": gene_name,
            "pval_threshold": float(arguments.get("pval_threshold", 0.05)),
        }

        url = f"{EPIGRAPHDB_BASE}/gene/drugs"
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])
        drug_associations = []
        for r in results:
            gene = r.get("gene", {})
            drug = r.get("drug", {})
            rel = r.get("r", {})
            drug_associations.append(
                {
                    "gene": gene.get("name"),
                    "drug": drug.get("label"),
                    "source": r.get("r_source"),
                    "pharmgkb_evidence": rel.get("pharmgkb_level_of_evidence"),
                    "cpic_level": rel.get("cpic_level"),
                    "pgx_on_fda_label": rel.get("pgx_on_fda_label"),
                    "guideline": rel.get("guideline"),
                }
            )

        return {
            "status": "success",
            "data": {
                "gene_drug_associations": drug_associations,
                "total_count": len(drug_associations),
            },
            "metadata": {
                "gene_name": gene_name,
                "source": "EpiGraphDB (CPIC, PharmGKB)",
                "description": "Pharmacogenomics drug-gene associations with clinical evidence levels",
            },
        }

    def _search_opengwas(self, arguments: dict) -> dict:
        """Search OpenGWAS database for GWAS studies by trait name using NLP."""
        query = arguments.get("query", "").strip()
        if not query:
            return {
                "status": "error",
                "error": "query parameter is required (e.g., 'body mass index', 'coronary heart disease')",
            }

        top_n = min(int(arguments.get("top_n", 10)), 50)
        params = {
            "text": query,
            "entity_type": "Gwas",
            "top_n": top_n,
        }

        url = f"{EPIGRAPHDB_BASE}/nlp/query/text"
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        results_data = data.get("results", {})
        # NLP endpoint returns {"results": {"results": [...], "clean_text": ...}}
        if isinstance(results_data, dict):
            inner_results = results_data.get("results", [])
        else:
            inner_results = results_data if isinstance(results_data, list) else []

        studies = []
        for r in inner_results[:top_n]:
            if r.get("meta_node") == "Gwas" or not r.get("meta_node"):
                studies.append(
                    {
                        "id": r.get("id"),
                        "trait": r.get("name") or r.get("text"),
                        "similarity_score": r.get("score"),
                        "meta_node": r.get("meta_node"),
                    }
                )

        return {
            "status": "success",
            "data": {
                "gwas_studies": studies,
                "total_found": len(studies),
            },
            "metadata": {
                "query": query,
                "source": "EpiGraphDB / IEU OpenGWAS (NLP search)",
                "description": (
                    "Search OpenGWAS GWAS studies by trait name similarity. "
                    "Use returned 'id' values (e.g., 'ieu-a-2') in MR analyses."
                ),
            },
        }
