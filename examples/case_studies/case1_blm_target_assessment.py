#!/usr/bin/env python3
"""Case 1: Is BLM a context-selective anticancer target, and is ML216 developable?

Reproduces the first case study from
https://aiscientist.tools/posts/tooluniverse-case-studies

The steps below are the tool calls in the order the AI scientist made them.
Every number printed with a "(published: ...)" annotation is one that appears
either in the post or in the supplementary note it condenses (arXiv:2509.23426),
so a run either reproduces the published values or shows exactly where it
drifted. Intermediate values such as ACMG scores, PDB accessions, per-context
DepMap effects and PubChem CIDs come from the supplementary note.

Run:
    python case1_blm_target_assessment.py

Needs network access; no API keys. Step 7 needs the ``ml`` extra
(``pip install 'tooluniverse[ml]'``) for the ADMET-AI models.
"""

from __future__ import annotations

from _common import (
    call,
    footer,
    header,
    is_error,
    load_universe,
    note_unavailable,
    report,
    step,
)

BLM_ENSEMBL = "ENSG00000197299"
BLM_UNIPROT = "P54132"
# BLM c.520C>T (p.Gln174Ter), GRCh38.
VARIANT = {"chr": "chr15", "pos": 90749788, "ref": "C", "alt": "T", "genome": "hg38"}


def main() -> None:
    header(
        "Case 1: BLM as a cancer risk gene and a possible target",
        "BLM loss-of-function predisposes to cancer by compromising genome "
        "maintenance.\n          Is BLM nevertheless a context-selective "
        "anticancer target, and is its\n          inhibitor ML216 a developable lead?",
    )
    tu = load_universe()

    # ------------------------------------------------------------------
    step(1, "Resolve and annotate the gene")
    search = call(
        tu,
        "OpenTargets_multi_entity_search_by_query_string",
        queryString="BLM",
        entityNames=["target"],
    )
    hits = search.get("search", {}).get("hits", []) if not is_error(search) else []
    ensembl = next((h["id"] for h in hits if h.get("entity") == "target"), None)
    report("BLM Ensembl gene", ensembl, BLM_ENSEMBL)

    go = call(
        tu, "OpenTargets_get_target_gene_ontology_by_ensemblID", ensemblId=BLM_ENSEMBL
    )
    if not is_error(go):
        terms = go.get("target", {}).get("geneOntology", [])
        labels = [(t.get("term", {}).get("label") or "").lower() for t in terms]
        repair = [
            label
            for label in labels
            if "repair" in label or "helicase" in label or "recombination" in label
        ]
        report("GO terms returned", len(terms))
        report("of which DNA-repair / helicase / recombination", len(repair))
        for label in sorted(set(repair))[:4]:
            print(f"    - {label}")
        print("  Read: a genome-maintenance helicase, i.e. the kind of gene whose")
        print("  loss promotes tumours, so the genetics counsel caution about")
        print("  inhibiting it rather than support it.")

    # ------------------------------------------------------------------
    step(2, "Quantify the cancer-risk genetics")
    diseases = call(
        tu,
        "OpenTargets_get_diseases_phenotypes_by_target_ensembl",
        ensemblId=BLM_ENSEMBL,
    )
    if not is_error(diseases):
        rows = (
            diseases.get("target", {}).get("associatedDiseases", {}).get("rows", [])
            or []
        )
        count = diseases.get("target", {}).get("associatedDiseases", {}).get("count")
        report("disease associations", count, "464")
        if rows:
            report("top association", rows[0].get("disease", {}).get("name"))

    # ------------------------------------------------------------------
    step(3, "Classify the patient's variant")
    clinvar = call(tu, "ClinVar_search_variants", gene="BLM")
    if not is_error(clinvar):
        report("ClinVar BLM variant records", clinvar.get("total_count"))

    genebe = call(tu, "GeneBe_classify_variant", **VARIANT)
    if not is_error(genebe):
        report("c.520C>T ACMG class", genebe.get("acmg_classification"), "Pathogenic")
        report("ACMG score", genebe.get("acmg_score"), "12")
        report("transcript", genebe.get("transcript"), "NM_000057.4")
    print("  Read alone, this argues against inhibiting BLM at all.")

    # ------------------------------------------------------------------
    step(4, "Test for a context-selective dependency (the turning point)")
    depmap = call(
        tu, "OpenTargets_get_target_depmap_essentiality", ensemblId=BLM_ENSEMBL
    )
    if not is_error(depmap):
        target = depmap.get("target", {})
        entries = target.get("depMapEssentiality", []) or []
        n_lines = sum(len(e.get("screens", []) or []) for e in entries)
        report("pan-essential?", target.get("isEssential"), "false (not pan-essential)")
        report("cancer cell lines screened", n_lines, "1,258")

        all_effects = [
            s["geneEffect"]
            for e in entries
            for s in e.get("screens", []) or []
            if isinstance(s.get("geneEffect"), (int, float))
        ]
        if all_effects:
            mean_effect = sum(all_effects) / len(all_effects)
            dependent = [v for v in all_effects if v < -0.5]
            report("mean gene effect", f"{mean_effect:+.2f}", "-0.18")
            report(
                "lines dependent at < -0.5",
                f"{len(dependent)}/{len(all_effects)} "
                f"({100 * len(dependent) / len(all_effects):.1f}%)",
                "94/1,258 (7.5%)",
            )

        # Where the dependency concentrates, by cancer type and by tissue.
        def group_means(key):
            buckets = {}
            for entry in entries:
                for screen in entry.get("screens", []) or []:
                    effect = screen.get("geneEffect")
                    if not isinstance(effect, (int, float)):
                        continue
                    label = (
                        screen.get("diseaseFromSource")
                        if key == "disease"
                        else entry.get("tissueName")
                    )
                    if label:
                        buckets.setdefault(label, []).append(effect)
            return sorted(
                (
                    (sum(v) / len(v), label, len(v))
                    for label, v in buckets.items()
                    if len(v) >= 5
                )
            )

        print("  Most-dependent cancer types (mean gene effect, n>=5 lines):")
        for mean, label, n in group_means("disease")[:3]:
            print(f"    {label:<48} {mean:+.2f}  (n={n})")
        print("  Most-dependent tissues:")
        for mean, label, n in group_means("tissue")[:3]:
            print(f"    {label:<48} {mean:+.2f}  (n={n})")
        print("  Published: mature T/NK-cell neoplasms -0.47 (n=8), cutaneous SCC")
        print("  -0.44 (n=5), peripheral nervous system / neuroblastoma -0.33 (n=48)")
        print("  Read: not broadly essential, but dependency concentrates in a few")
        print("  contexts, which is what a therapeutic window would look like.")

    # ------------------------------------------------------------------
    step(5, "Retrieve the structure and check its reliability")
    af = call(tu, "alphafold_get_summary", qualifier=BLM_UNIPROT)
    if not is_error(af):
        entry = af.get("uniprot_entry", {})
        report("protein length", entry.get("sequence_length"), "1,417")
        structures = af.get("structures", []) or []
        if structures:
            summary = structures[0].get("summary", {})
            report("AlphaFold model", summary.get("model_identifier"), "AF-P54132-F1")
        print("  The prediction is mixed-confidence: confidently folded catalytic")
        print("  regions separated by low-confidence interdomain linkers.")

    pdbe = call(tu, "PDBe_get_uniprot_structure_coverage", uniprot_id=BLM_UNIPROT)
    if not is_error(pdbe):
        data = pdbe.get(BLM_UNIPROT, {})
        pdb_ids = sorted(
            {e["name"].lower() for e in (data.get("data") or []) if e.get("name")}
        )
        report("experimental PDB entries", len(pdb_ids))
        for wanted in ("7auc", "4cgz", "4o3m"):
            report(
                f"  helicase-core structure {wanted.upper()} present", wanted in pdb_ids
            )
        print("  Read: anchor structural reasoning on these experimental structures,")
        print("  not on the mixed-confidence prediction.")

    # ------------------------------------------------------------------
    step(6, "Ground the therapeutic context in the literature")
    lit = call(
        tu,
        "EuropePMC_search_articles",
        query="WRN helicase synthetic lethal microsatellite instability cancer",
        limit=5,
    )
    if not is_error(lit) and isinstance(lit, list):
        report("articles returned", len(lit))
        for article in lit[:3]:
            print(f"    - {str(article.get('title'))[:88]}")
        print("  Read: BLM's paralog WRN is the clinically validated synthetic-lethal")
        print("  target in this family, which is the precedent the BLM hypothesis")
        print("  is built on by analogy.")

    # ------------------------------------------------------------------
    step(7, "Find and triage the chemical matter")
    probes = call(
        tu,
        "OpenTargets_get_chemical_probes_by_target_ensemblID",
        ensemblId=BLM_ENSEMBL,
    )
    if not is_error(probes):
        entries = probes.get("target", {}).get("chemicalProbes", []) or []
        ml216 = next((p for p in entries if p.get("id") == "ML216"), None)
        if ml216:
            report("ML216 flagged high quality?", ml216.get("isHighQuality"), "false")
            report("ML216 mechanism", ml216.get("mechanismOfAction"), "['inhibitor']")
            print("  Read: the platform itself marks ML216 a probe, not a lead.")

    cid_payload = call(tu, "PubChem_get_CID_by_compound_name", name="ML216")
    cid = None
    if not is_error(cid_payload):
        cid = (
            cid_payload.get("IdentifierList", {}).get("CID", [None])[0]
            if isinstance(cid_payload, dict)
            else None
        )
        report("ML216 PubChem CID", cid, "49852229")

    smiles = None
    if cid:
        props = call(
            tu,
            "PubChem_get_compound_properties_by_CID",
            cid=cid,
            properties="MolecularWeight,SMILES,ConnectivitySMILES,IUPACName",
        )
        if not is_error(props):
            entry = props.get("PropertyTable", {}).get("Properties", [{}])[0]
            # Prefer the stereochemistry-bearing SMILES where one exists; ADMET-AI
            # scores flat and stereo forms differently. ML216 has no stereocentre,
            # so the two agree here.
            smiles = entry.get("SMILES") or entry.get("ConnectivitySMILES")
            report("molecular weight", entry.get("MolecularWeight"), "383 Da")
            report("SMILES", smiles)

    if smiles:
        physchem = call(
            tu, "ADMETAI_predict_physicochemical_properties", smiles=[smiles]
        )
        if is_error(physchem):
            note_unavailable("ADMETAI_predict_physicochemical_properties", physchem)
        else:
            values = physchem.get(smiles, physchem)
            report(
                "QED (drug-likeness)", round(values.get("QED", float("nan")), 3), "0.66"
            )
            report(
                "Lipinski rules passed", values.get("Lipinski"), "4 of 4 (0 violations)"
            )

        tox = call(tu, "ADMETAI_predict_toxicity", smiles=[smiles])
        if is_error(tox):
            note_unavailable("ADMETAI_predict_toxicity", tox)
        else:
            values = tox.get(smiles, tox)
            report(
                "DILI (liver injury)",
                round(values.get("DILI", float("nan")), 3),
                "0.99",
            )
            report("hERG (cardiac)", round(values.get("hERG", float("nan")), 3), "0.56")
            report(
                "AMES (mutagenicity)",
                round(values.get("AMES", float("nan")), 3),
                "0.16",
            )

        # Is the DILI signal specific to this molecule, or to the scaffold?
        analogs = call(
            tu,
            "ChEMBL_search_similar_molecules",
            query=smiles,
            similarity_threshold=70,
            max_results=5,
        )
        if is_error(analogs):
            note_unavailable("ChEMBL_search_similar_molecules", analogs)
        else:
            # The tool returns a list of query molecules, each carrying its own
            # normalised "similar_molecules" list; the analog SMILES live one
            # level down under "smiles", not in the raw ChEMBL
            # molecule_structures shape.
            analog_smiles = []
            for group in analogs if isinstance(analogs, list) else []:
                for analog in group.get("similar_molecules") or []:
                    candidate = analog.get("smiles")
                    if candidate and candidate != "N/A":
                        analog_smiles.append(candidate)
            analog_smiles = analog_smiles[:5]
            if analog_smiles:
                analog_tox = call(tu, "ADMETAI_predict_toxicity", smiles=analog_smiles)
                if not is_error(analog_tox):
                    dili = [
                        analog_tox[s]["DILI"] for s in analog_smiles if s in analog_tox
                    ]
                    if dili:
                        report(
                            "DILI across close analogs",
                            f"{min(dili):.3f}-{max(dili):.3f}",
                            "0.987-0.992",
                        )
                        print("  Read: DILI stays pinned near its maximum across the")
                        print("  series while other liabilities move, which points at")
                        print("  the scaffold rather than at one molecule.")
            else:
                print("  [no analogs returned] ChEMBL_search_similar_molecules gave")
                print("  no similar molecules, so the scaffold comparison is skipped.")

    footer(
        {
            "Germline genetics": "argue against inhibiting BLM (a tumour suppressor to preserve)",
            "DepMap + WRN precedent": "support a narrower claim: a selective vulnerability in "
            "defined subtypes",
            "Conclusion": "BLM is a context-selective hypothesis to test, not a validated target",
            "ML216": "drug-like but scaffold-associated DILI liability; a probe, not a lead",
        }
    )


if __name__ == "__main__":
    main()
