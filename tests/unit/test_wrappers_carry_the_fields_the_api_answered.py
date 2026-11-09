"""Fields the upstream answered and the wrapper did not pass on.

The sibling file `test_wrappers_ask_for_what_they_promise.py` guards the 102
tools that declare a GraphQL query, where the selection set is in the config
and can be read statically. For the other 2,786 nothing static says what the
upstream offers, so the gap has to be measured from the call the tool already
makes -- which is what `scripts/audit_upstream_field_coverage.py` does and what
the weekly sweep now runs per shard.

These are the cases that measurement found and that the judgement rule from
devtu-silent-failures then confirmed: a dropped field is a defect when it is
the substance of what the tool's own description promises. Measured live on
2026-11-07, before the fix:

    gProfiler_enrichment      no effective_domain_size, so the N of the
                              hypergeometric test was absent and the reported
                              p_value could not be recomputed; no
                              intersection_genes though the description
                              promises "intersection genes"; and
                              meta.genes_metadata.failed was dropped, so a
                              gene list with one typo in it was enriched on the
                              rest in silence.
    GxA_get_experiment_       expressions were [{tissue, value: 381.0}] with
      expression              the row's own expressionUnit ("tpms") dropped.
    GEO_search_chipseq_       n_samples: 82 and no sample accessions, while
      datasets                the description said GSM records were "excluded
                              upstream" -- true of the esearch entry-type
                              filter, not of the per-series sample list the
                              esummary answers.
    OrthoDB_search_groups     /search answers `data` (bare ids) and `bigdata`
                              (the full record: name, level_name, present_in,
                              gene_count). Only the ids were read, and a /tab
                              request per group then fetched a subset back.
    FlyBase_get_gene_         interactorARole "suppressed gene" and
      interactions            interactorBRole "suppressor gene" dropped, so a
                              suppression result named a pair and not a
                              direction; and no reference, so it could not be
                              cited.
    EBIProteins_get_hpp_      evidence source.properties -- Best Probability,
      peptides                Number of PSMs, Times of observations -- dropped
                              from "the stringent HPP evidence set".
    MaveDB_get_gnomad_        no faf95Max, the filtering allele frequency ACMG
      variants                BA1/BS1 is read against; no variantLinks, the
                              join back to the score set the tool exists for.
    DisGeNET_search_gene      7 of 37 fields: no disease_vocabularies (MONDO,
                              DO, MeSH), no scoreBreakdown, and of the
                              "evidence counts" the description promises, only
                              the PMID count.
    ComplexPortal_get_        GO cross-references without `qualifier`, which is
      complex                 the aspect ("cellular component"), and subunits
                              without bioRole or linkedFeatures.
    DOAJ_search_articles      `keywords` was built from bibjson.subject (the
                              journal's LCC class) while bibjson.keywords -- the
                              article's own terms -- was never read, so the
                              field named keywords held neither one under its
                              own name.
    Planteome_search_         no assigned_by, though the description promises
      annotations             annotations "across evidence types and source
                              databases", and no evidence_with, so an IEA could
                              not be checked.
    ExpressionAtlas_get_      said the API "does not expose per-experiment
      experiment              design ... through this endpoint". Half true:
                              experiment.experimentalFactors really is null,
                              and the design is in columnHeaders in the same
                              response, 29 assay groups the tool did not read.
    UniProtTaxonomy_get_      no otherNames, for a tool whose description calls
      taxon                   itself "essential for cross-referencing species".
    MediaDive_search_media    no link, and `description` and `reference` are
                              null for most of the catalogue.
    IDR_search_images         1,000 hits across studies with no plate, well,
                              project or dataset, so `study` named the
                              container and nothing located the image in it.
    Synapse_list_children     no benefactor_id, the entity whose access rules
                              govern the child.
    GOAPI_get_genes_by_       `evidence_type`, `evidence_label` and `reference`
      function                are not keys of a GO association. The API sends
                              `evidence`, `evidence_types` and `publications`,
                              so every annotation either GO tool ever served
                              carried a null evidence code and no references.
                              And NOT annotations went through the ordinary
                              branch: of the first 400 associations of
                              GO:0006915, one is `negated: true` with
                              `qualifier: ["not"]` -- MGI:1341836 Trpv2, by
                              direct assay -- returned as a gene with the
                              apoptotic process.
    MAGICapp_list_guidelines  matched on five fields and returned three of
                              them: a query naming an organisation came back
                              with no institution and no description. With
                              them went lastEdit (2026-11-07 against a
                              publishDate of 2015-02-01 on the first public
                              row), publishLastSearchDate, and
                              isLatestPublished -- false on both top stroke
                              hits, while the tool tells the caller to pass
                              that publishedId on.
    PubChemBioAssay_search_   aid, name, source, method, targets, has_score:
      by_gene                 nothing of how big the screen was. AID 902 holds
                              125,394 compounds, 1,890 of them active. Protocol
                              and Comment reached no tool at all, and the
                              sibling summary cut Description to three
                              paragraphs in silence.
    DANDI_search_datasets     counts from the published version, while
                              get_dataset and list_assets read the draft, with
                              nothing naming either. 000036 published
                              2023-05-15 against a draft modified 2026-02-17.
    miRBase_get_mirna_        no pub_id, the one key that tells apart the
      publications            duplicate-PMID records the tool's own metadata
                              warns about.
    gather_drug_profile       80 ChEMBL synonyms as flat strings capped at 15.
                              Aspirin's are 65 TRADE_NAME, 8 OTHER, 3
                              RESEARCH_CODE and one each of ATC, BNF, FDA and
                              MERCK_INDEX, and the 15 shown are alphabetically
                              first, so all brands.
    ClinVar_search_by_region  a pathogenic copy-number loss reported as a
                              span. The 30,531-base one over chr7:155593770
                              removes SHH and the 668,505-base one removes
                              five genes including EN2 -- `genes` was dropped
                              entirely, and ClinVar record 147398 lists 696 of
                              them. The VCV accession and the review status
                              went too, so the record could not be cited and
                              its classification could not be weighed.
    DbGaP_get_study /         a study's condition as ten free-text strings
      _search_studies         and no code. phs000681's 34 condition entries
                              are ONE MeSH coding -- D003924, "Diabetes
                              Mellitus, Type 2" -- plus 32 synonym rows whose
                              own `code` is a sentence, and the handler's
                              dedupe comment already said so. It kept the
                              texts and dropped the identifier, and the UMLS
                              CUI C0011860 beside it.
    UniProtTaxonomy_search    the synonyms round 26 added to
                              UniProtTaxonomy_get_taxon, missing from the
                              search beside it. Taxon 9606 carries 17, and a
                              query for "human" matches the Denisovan taxon
                              through its own -- which the row could not show.
                              `active` and the parent went too.
    Ensembl_get_assembly_     GRCh38's 194 top-level regions are 25
      info                    chromosomes and 169 scaffolds. The counts said
                              194 and 25, so the cut was disclosed, and no
                              tool in the family returned the other 169, so a
                              caller needing KI270728.1's length had no route
                              to it. `coord_system`, which the chromosome
                              filter reads, was not reported either.
    ZFIN_get_gene_expression  an expression annotation as two strings.
                              "anal fin" at "Larval:Days 14-20" cannot be
                              joined to an anatomy ontology; the same record
                              carries UBERON:0000026 and UBERON:0001062 in
                              termIds and ZFA:0001162 under
                              expressionPattern. The assay went too --
                              MMO:0000658, RNA in situ, which is a different
                              weight of evidence from a sequencing assay --
                              and so did the figure the call was read off,
                              ZFIN:ZDB-FIG-140307-27.
    proteins_api_get_         a tool that promises "mass spectrometry
      proteomics              evidence" and returned 36 features and none of
                              the pointers to the evidence. The entry it
                              already fetched lists 780 cross-references, of
                              which 21 are proteomics resources: PeptideAtlas,
                              MassIVE, jPOST, eleven ProteomicsDB entries,
                              PhosphoSitePlus, and GlyGen with "27 sites, 13
                              N-linked glycans" in its properties. Its schema
                              declared a bare array while the tool returns a
                              dict envelope.
    NCIThesaurus_get_concept  `definitions[0]` as THE definition. C3224 has
      (definitions)           four -- NCI-GLOSS, CDISC, NICHD and NCI -- and
                              the first is the patient-facing glossary one,
                              returned with no source while the thesaurus's
                              own NCI definition sat fourth. Found by
                              grepping the module for `[0]` after the
                              SmartAPI finding, not by a shard.
    SmartAPI_search_apis      `base_url: servers[0]["url"]` handed back a
                              DEVELOPMENT url as the API's base url for any
                              entry that lists development first, which the
                              CFDE Gene Regulation hub does:
                              genboree.org/cfde-gene-dev against
                              genboree.org/cfde-gene. A wrong value, not a
                              missing one. `info.contact` was requested in
                              _SEARCH_FIELDS and never read, so the
                              registry's answer to "who maintains this" was
                              fetched and discarded on every search.
    OSDR_search_studies       no study descriptions, in a search whose hits a
                              caller has to choose between, and no
                              "Study Assay Technology Platform" -- which is
                              often the only one of the three assay fields
                              populated: assay_technology_type is empty on the
                              first microgravity hit while the platform reads
                              GPL1219. No Project Type either.
    cBioPortal_get_copy_      the bare profile id. Round 26 gave the mutations
      number_alterations      path the chosen profile's own record and how the
                              id was arrived at, and left this path unchanged,
                              so a CNA caller could not tell a GISTIC profile
                              from a log2 one nor a matched id from a guess.
                              The profile's description is also where the value
                              legend lives -- "-2 = homozygous deletion ...
                              2 = high level amplification" -- without which
                              the integers in `data` are uninterpretable.
    GeneBe_classify_variant   a ClinVar conflict with no way to weigh it. The
                              row returned clinvar_classification
                              "Conflicting classifications of pathogenicity"
                              for BRAF V600E and dropped
                              clinvar_review_status ("criteria provided,
                              conflicting classifications") and
                              clinvar_submissions_summary ("P:3 LP:1 US:5
                              O:1" -- five of ten uncertain). `consequences`
                              went entirely: 43 transcripts, with MANE Select
                              marking NM_004333.6, reported as one
                              `transcript` string. The batch handler in the
                              same module returns the raw record whole, so
                              none of it cost a request.
    InterPro_get_structures_  the THIRD endpoint of this family to drop its
      for_domain              `entries` block, after entries_for_protein in
                              round 26 and proteins_by_domain in round 29. The
                              row said which structures contain PF00870 and
                              nothing about the containment: not the chain
                              (A and C for 1gzh), not the residues in either
                              frame (100-288 in UniProt, 6-194 in the
                              structure with auth 100-288 beside it), not the
                              6.8e-60 e-value.
    NDEx_search_networks      the sibling of round 29's fix. The search row
                              dropped `properties`, where the fields a caller
                              picks a network BY live: organism Homo sapiens,
                              disease cancer, tissue breast carcinoma, methods
                              coexpression analysis -- and on the second hit a
                              non-commercial licence and a citation. The
                              300-character description cut was undisclosed.
    NCIThesaurus_get_concept  seventeen synonyms with nothing marking which
                              is the concept's name. The row read `termType`,
                              which is the term's role in its SOURCE
                              terminology -- ten of C3224's rows are "PT",
                              each a different source's preferred term, and
                              CDISC's is "MELANOMA, MALIGNANT". NCIt's own
                              name sits on the one row whose annotation
                              property is Preferred_Name, and that row has no
                              termType at all, so it came back as
                              {"type": null, "source": null}.
    IGSR_search_populations   no dataCollections, so nothing said whether a
                              population has alignments or variants, what
                              sequencing they came from, or what reuse policy
                              governs them -- while the sibling sample search
                              already read the same block for its titles.
    PGSCatalog_search_traits  a trait search in a score catalogue that
                              reported how many scores a trait has and not
                              which: `associated_pgs_ids` holds 88 for
                              MONDO_0005010 and `child_associated_pgs_ids`
                              another 8 that score/search?trait_id= does not
                              return at all, so they were reachable through
                              no call. And no trait_synonyms, though the query
                              "coronary artery disease" is a synonym of the
                              label it matched, "coronary artery disorder".
    Alliance_get_disease_     evidence codes as prose only. Alliance sends
      genes                   {"curie": "ECO:0000270", "abbreviation": "IEP",
                              "name": ...} and the row kept the name, so
                              neither the code a paper cites nor the id a
                              machine reads survived. The relation went too:
                              "is_implicated_in" and "is_marker_for" are 35
                              and 23 on one page of DOID:162 and are
                              different claims.
    NIHDSLD_get_label         a tool that promises "one dietary supplement's
                              full label" returned the ingredient table and
                              none of the label's 23 statements, four of which
                              are precautions -- "Precautions re: Pregnant or
                              Nursing or Prescription Medications", "KEEP OUT
                              OF THE REACH OF CHILDREN". The 9 other
                              ingredients went too, though the description
                              promises "every ingredient", as did the footnote
                              that says what the percent daily values it does
                              return are a percentage of.
    MGI_get_phenotypes /      a phenotype returned as free text with no term
      ZFIN_get_gene_          and no id, in a tool whose description says it
      phenotypes              returns "Mammalian Phenotype (MP) ontology
                              annotations". All 125 annotations on MGI:97490
                              carry MP:0005193 and its definition. The row
                              relation ("is_implicated_in") and each
                              annotation's ("has_phenotype") are different
                              claims and both were dropped, with the data
                              provider and the genotype the phenotype was
                              seen in -- MGI:2170872, not the queried
                              MGI:97490.
    FDAGSRS_get_substance     a name's `references` are uuids into the
                              record's own 78-entry references array, where
                              the citation is ("EP 6.5", docType FDA_SRS).
                              None of it reached the caller, though the
                              module docstring promises "regulatory
                              references from the ?view=full record", and a
                              code's `comments` -- the ATC classification path
                              a WHO-ATC code stands for -- went with it.
    FinnGen_list_phenotypes   no gc_lambda, the genomic-control inflation
                              factor, though it is on all 2,470 phenotypes of
                              the list endpoint and the single-phenotype
                              handler beside it already returned it. For a
                              list used to pick a GWAS to analyse that is the
                              "is this usable" signal, and
                              AB1_TUBERCULOSIS_MILIARY reads 0.38 at the 0.5
                              quantile. No assoc_files either, the summary
                              statistics the phenotype is for.
    ThreeDBeacons_get_        a list of 375 structures with no model_format,
      structures              so the download URL the description promises came
                              without the format needed to parse it (MMCIF on
                              373, PDB on 2); no sequence_identity, so a model
                              covering p53 at 50% read like one at 100%; and
                              none of the 1,220 entity records that say which
                              chains and which bound ligands each structure
                              holds.
    get_joint_associated_     the differential was intersected over disease
      diseases_by_HPO_ID_     LABELS while `subject`, the MONDO curie, sat
      list                    unread on all 5,331 associations of HP:0001250.
                              One disease whose label differs between two legs
                              dropped out; two diseases sharing a label
                              vouched for each other.
    PDBe_KB_get_ligand_       1,136 residue codes dropped: the rows were
      sites / _interface_     `{start, end}` positions in tools that promise
      residues                "binding site residues" and "interface
                              residues". P04637's first NAD-binding residue is
                              LYS 382 in UniProt numbering, and both the
                              residue and the frame were gone, along with
                              interactingPDBEntries -- the structures where
                              the contact is actually seen, a subset of the
                              allPDBEntries the row did return -- and the
                              ligand's SMILES, atom count and significance.
    DepMap_get_cell_lines     2 of a /models item's 24 attributes. Nine of the
                              rest are `*_available` flags: PK-59 is
                              crispr_ko_available false and SNU-1033 true, and
                              a knockout screen could not tell them apart.
                              mutations_per_mb 24.79 and ploidy_wes 3.51 went
                              too, while the description promised a tissue and
                              a cancer type this endpoint does not carry.
    iNaturalist_get_taxon /   a conservation status reduced to "G4" -- a
      _search_taxa            NatureServe rank the schema called IUCN -- with
                              the authority, the place and the other 28
                              statuses of the same response dropped, among
                              them "Special Concern" under the Canadian
                              Species at Risk Act. And no establishment_means,
                              so nothing said the monarch is introduced in
                              Australia and native elsewhere.
    NDEx_get_network          a network returned as a bare topology: 82 nodes
                              carry 378 nodeAttributes and 118 edges 2,222
                              edgeAttributes -- Saintscore, BFDR,
                              logOddsScore, Entropy, WD -- and the rows held
                              id/name/represents and id/source/target/
                              interaction. The first edge is Saintscore 0.07,
                              BFDR 0.68, and read like any other.
    InterPro_get_proteins_    the `entries` block of each hit, which says
      by_domain               where the domain sits: IPR011615 at 106-281 of
                              A0A016WYN1's 439 residues, as a `domain` entry.
                              The row answered which protein and nothing
                              about the containment.
    Mondo_search_disease      six fields where its twin on the same /search
                              endpoint keeps fifteen: no score (287.25 for
                              "breast cancer" against 51.77 for "sporadic
                              breast cancer"), no match_type, no synonyms.
    MCSA_get_entry /          a catalytic residue numbered 45 where the PDB,
      MCSA_search_enzymes     the papers and the entry's own mechanism text
                              all say 70 (`resid` against `auth_resid`); roles
                              collapsed from 38 records to a set of names, so
                              `function_type` -- reactant, interaction or
                              spectator -- was gone; `reaction_name` read from
                              a key M-CSA does not send, null on every entry,
                              while the reaction's compounds and both curated
                              mechanisms with their 12 references reached
                              nobody.
    hca_search_projects       four fields, and the first project the endpoint
                              returns is Mus musculus with nothing saying so.
                              No libraryConstructionApproach ("10x 3' v2"), no
                              cell count (1,330,000), no donor age or count,
                              and organ and disease read off the first
                              specimen and donor of several.
    hca_get_file_manifest     a download manifest with no sha256, version or
                              uuid, and no isIntermediate to tell a final
                              matrix from an intermediate.
    OPM_search_structures     `description` is null on all 74 rhodopsin rows
                              while `comments` holds the prose; and no
                              subunit_segments (74/74, the number of bilayer
                              crossings), species (74/74), uniprotcodes
                              (71/74), topology_subunit (74/74) or tilterror
                              (37/74) beside the thickness error the row kept.

NOT DEFECTS, recorded so the next sweep does not re-litigate them. The 77
`FDA_get_drug_names_by_*` tools declare `return_fields: ["openfda.brand_name",
"openfda.generic_name"]` in the config and are named for it; the label sections
they skip are what their sibling tools return. ComplexPortal's `dbdefinition`
and `qualifierDefinition` are paragraphs of ontology prose. Planteome's
`*_closure*` fields restate the term's own hierarchy. GEO's `translationstack`
and `idlist` are esearch internals, and the query expansion is already
disclosed as `query_disclosure`. MaveDB's `recordType`, `id` and
`creationDate` are database bookkeeping. Ensembl's constrained elements carry
`feature_type: "constrained"` on all 20 rows -- the request parameter echoed
back, and the tool's own name. GO's `subject.iri`, `object.iri` and
`taxon.iri` are each the returned curie in URL form, and an association's `id`
is a hex blob of the fields around it. DANDI's `embargo_status` is "OPEN" on
every record an unauthenticated search can reach: `?embargoed=true` answers
401, and this tool sends no token. SABIO-RK's `docs[].Json` is a ~8 kB JSON
string parsed into `source_record`, so no string value survives to be
matched while the whole record reaches the caller. ProteomicsDB's
`__metadata.type`/`uri` are OData envelope internals. CellPainting's flagged
fields are the OMERO data owner's name, email and institution.
`ClinicalTrials_get_field_values` was flagged for `ranges[].sizeRange`, which
belongs to an auxiliary `/stats/size` request it makes for one denominator;
those rows are the output of `ClinicalTrials_get_stats_size`, the tool that
owns that endpoint. The audit records responses per tool run, so a wrapper
that calls a sibling endpoint is flagged for every field of it -- check which
request a flagged path came from before reading it as a drop.
`MARRVEL_get_omim_phenotypes` disclaims its own omission in so many words:
"Allelic-variant narratives are not returned by this phenotype-focused tool,
and metadata states that limitation explicitly." An earlier round put that
sentence there and the metadata does say it, so the 27 allelic-variant
records behind `allelic_variant_count` are a disclosed selection rather than
a drop. InterPro's domain-architecture endpoint keeps `proteins[].accession`
and `metadata.source_database` out for different reasons: the first is the
queried accession echoed back and the second is the constant "pfam" from the
request path.

`OpenFDA_get_approved_products` is about products and formulations, and its
submissions reach the caller through `FDA_OrangeBook_get_approval_history`,
which returns all 6 of ANDA078083's with their type, status, dates, class
codes and documents. I first recorded that pointer as BROKEN after reading
the result's `approval_history` key, which does not exist -- the key is
`submissions` -- so the pointer test needs the sibling's real output shape,
not a guess at it. `PharmGKB_get_variant_annotations` passes the raw
annotation record through unprojected; its 1,682 flagged diplotype ids are
the rows beyond the requested page, disclosed by total_results, has_more and
next_offset. OSDR's `Study Person` name parts are composed into "Hanjoong
Jo" by `_person` via `key.title()`.

A POINTER CAN BE TESTED, and these three were. `FDAGSRS_search_substances`
returns ten synonyms with the total and a truncation flag, and the citations
its names' reference uuids point at are returned in full by
`FDAGSRS_get_substance` for the same UNII -- verified, because round 33 is
what made that true. `MassIVE_search_datasets` omits contacts and
publications, and `MassIVE_get_dataset`'s description promises both and
delivers them for the same accession. Both pointers hold, which is exactly
what did NOT happen for PGSCatalog_search_traits' child scores: same test,
opposite answer, and the test is one request.

`OSL_get_efo_id_by_disease_name` names its own omission: its description
says it returns `{efo_id, name}` and points at the richer sibling for the
IRI and synonyms. NDEx's cartesianLayout coordinates and cyVisualProperties
are how to draw the graph, not what is in it. SGD's interaction `id` is an
internal annotation row id (7574210) in a row that already carries the
interaction and experiment types, the partners, the source and the
reference. Reactome's interactor `id` is internal and `accURL` is
`purl.uniprot.org/uniprot/{acc}` built from the `acc` beside it.
`OncoTree_list_tissues` returns the unique set of tissue NAMES, which is what
its description says twice and what `OncoTree_search` takes as
`field: "tissue"`; the per-tumour-type codes, colors and parents belong to
`OncoTree_search`, which returns every upstream field. USGS streamflow's
`features[].type` is the GeoJSON constant "Feature" and `geometry.type` is
"Point". PlantReactome's `refEntities[].dbId` is an internal Reactome id.

The openFDA `*_table` flags are not a defect and have now cost triage in
four shards, so here is the mechanism. `extract_nested_fields` already
copies `<section>_table` for every requested section, HTML intact and never
keyword-trimmed, and the nine FDADrugLabel tools named for a section with a
table sibling do return it: ciprofloxacin through
`FDA_get_dosage_and_storage_information_by_drug_name` comes back with
`dosage_and_administration_table` holding the Adult Dosage Guidelines grid.
The flags belong to the `FDA_get_drug_name_by_*` and
`FDA_get_drug_names_by_*` family, whose `return_fields` are the dotted
`openfda.brand_name` / `openfda.generic_name`; the table loop skips dotted
fields, and those tools are named for returning names. Check which tool in a
family a flagged path belongs to before reading it as a drop.


MassIVE's contacts and publications arrive as PSI-MS CV groups; the wrapper
returns each term's readable label and value, and the flagged `cvLabel` is
"MS" on every entry while `accession` is the ontology id of a term whose
label is already there. HuBMAP's provenance lineage reports a
`contributor_count` and points at HuBMAP_get_dataset, which returns the
contributor records in full -- a deliberate split recorded in the handler's
own comment. GoaT's `lineage[].node_depth` is the array index plus one on all
31 entries of Homo sapiens, and `taxon_names[].source_url` is the source
database's homepage, which `source` already names.

Alliance's `phenotypeAnnotationSubject.curie` is an AGRKB key
("AGRKB:108000000094293") and `primaryExternalId` beside it is the
model-organism id a caller can use, so the curie is not reported and the
external id is. ZFIN and WormBase compose free-text phenotype statements
rather than annotating single ontology terms, so their `phenotype_terms` is
empty by upstream design -- measured: 0 terms across 18 WormBase rows and 2
ZFIN rows, against 125 of 125 for MGI.

`FDA_OrangeBook_get_te_code` summarises the submission history to the
original approval date and a count, and `_submission_summary`'s own
docstring says why: "The full history is
FDA_OrangeBook_get_approval_history's job, so this summarises rather than
copies." That sibling returns each submission's documents with their type,
url and date -- the fields flagged here. Reactome's `orthologousEvent[].dbId`
is internal and `stIdVersion` is the `stId` the row already returns plus a
version suffix. RCSB's `pdbx_audit_revision_item` is the wwPDB audit trail,
which mmCIF item changed in which revision. iDigBio's
`attribution[].contacts[]` are collectors' personal names and email
addresses.

An AGGREGATION is the sharpest form of the transformation rule.
`FAERS_analyze_temporal_trends` was flagged for `results[].time` on 2,010
values: openFDA's `count=receivedate` facet returns one bucket per day, and
the handler reads `time` and sums the buckets into the years its description
promises. Every one of the 2,010 daily strings is a zero-survivor because
the tool exists to collapse them, so a value audit cannot distinguish
aggregation from loss. Read what the tool says it returns before reading the
count.
DEFERRED, with the reason. `get_joint_associated_diseases_by_HPO_ID_list`
returns disease names and not their MONDO curies, so its answer cannot be
passed to another tool without re-resolving by name. Adding the ids means
changing the return shape, which its `return_schema` declares as a string
array and which two skills document in three checked-in copies: a contract
change rather than a dropped field. The intersection is keyed by the curie
now, which was the correctness half of the same omission.

Reactome's `evidencesURL` is the route to the 122
evidences behind an interactor's count, and it is a ~3 kB IntAct query URL
per interactor; a page of them would be most of the response. It belongs in
a per-interactor lookup rather than in the list, and no such tool exists yet.
"""

import json
import pathlib

import pytest

pytestmark = pytest.mark.unit

REPO = pathlib.Path(__file__).resolve().parents[2]
SRC = REPO / "src" / "tooluniverse"
DATA = SRC / "data"


def _source(module):
    path = SRC / module
    assert path.is_file(), f"{module} is not in src/tooluniverse"
    return path.read_text()


def _config(tool_name):
    for path in sorted(DATA.glob("*.json")):
        try:
            payload = json.loads(path.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(payload, list):
            continue
        for cfg in payload:
            if isinstance(cfg, dict) and cfg.get("name") == tool_name:
                return cfg
    raise AssertionError(f"{tool_name} is not in the catalogue")


# (wrapper module, upstream key it must read, why that key is the substance)
UPSTREAM_KEYS = [
    (
        "gprofiler_tool.py",
        "effective_domain_size",
        "N in the hypergeometric test; without it the reported p_value cannot be recomputed",
    ),
    (
        "gprofiler_tool.py",
        "intersections",
        "the intersection genes the description promises, not just their count",
    ),
    (
        "gprofiler_tool.py",
        "genes_metadata",
        "which submitted identifiers g:Profiler could not resolve",
    ),
    (
        "gxa_tool.py",
        "expressionUnit",
        "a bare 381.0 is not an expression level",
    ),
    (
        "epigenomics_tool.py",
        'uid_data.get("samples")',
        "the GSM accessions that identify the runs to download",
    ),
    (
        "epigenomics_tool.py",
        "pubmedids",
        "the publication behind the series",
    ),
    (
        "orthodb_tool.py",
        "bigdata",
        "the group records /search already returned beside the bare ids",
    ),
    (
        "orthodb_tool.py",
        'record.get("level_name")',
        "the taxonomic level a group is defined at, which is what tells two hits apart",
    ),
    (
        "alliance_genome_tool.py",
        "interactorARole",
        "which gene suppresses which; an interaction type alone has no direction",
    ),
    (
        "alliance_genome_tool.py",
        "shortCitation",
        "an interaction with no reference cannot be cited",
    ),
    (
        "ebi_proteins_ext_tool.py",
        'src.get("properties")',
        "Best Probability and the PSM counts are what make HPP evidence stringent",
    ),
    (
        "mavedb_tool.py",
        "faf95Max",
        "the filtering allele frequency ACMG BA1/BS1 thresholds are read against",
    ),
    (
        "mavedb_tool.py",
        "variantLinks",
        "the join between the score set and gnomAD, which is what the tool is for",
    ),
    (
        "disgenet_tool.py",
        "diseaseVocabularies",
        "the MONDO/DO/MeSH ids an association has to carry to be joined to anything",
    ),
    (
        "disgenet_tool.py",
        "scoreBreakdown",
        "what the association score is made of",
    ),
    (
        "disgenet_tool.py",
        "numCTsupportingAssociation",
        'an "evidence count" the description promises and only PMIDs supplied',
    ),
    (
        "complex_portal_tool.py",
        "qualifier",
        "on a GO cross-reference this is the aspect",
    ),
    (
        "complex_portal_tool.py",
        "linkedFeatures",
        "which region of a subunit binds which partner",
    ),
    (
        "complex_portal_tool.py",
        "bioRole",
        "what a subunit does in the complex, not just what it is",
    ),
    (
        "doaj_tool.py",
        'b.get("keywords")',
        "the article's own keywords, as opposed to the journal's subject class",
    ),
    (
        "doaj_tool.py",
        "affiliation",
        "what tells two authors of the same name apart",
    ),
    (
        "planteome_tool.py",
        "assigned_by",
        'the "source databases" the description promises',
    ),
    (
        "planteome_tool.py",
        "evidence_with",
        "what an IEA annotation was inferred from, which is what makes it checkable",
    ),
    (
        "expression_atlas_tool.py",
        "columnHeaders",
        "the experiment's design, in the same response that leaves experimentalFactors null",
    ),
    (
        "uniprot_taxonomy_tool.py",
        "otherNames",
        "the synonyms a cross-reference is resolved through",
    ),
    (
        "mediadive_tool.py",
        'row.get("link")',
        "the only handle on a medium whose description and reference are null",
    ),
    (
        "idr_searchengine_tool.py",
        "plate_name",
        "where a screen's image sits, which is how the paper refers to it",
    ),
    (
        "synapse_tool.py",
        "benefactorId",
        "the entity whose access rules govern the child",
    ),
    # Second round: the families the catalogue-wide run ranked highest.
    (
        "omnipath_tool.py",
        "_omnipath_references",
        "the papers behind an interaction; `sources` names the databases, not the evidence",
    ),
    (
        "omnipath_tool.py",
        '"source": item.get("source"),\n                    "consensus_score"',
        "whether an intercell row is about a protein, a complex or a miRNA",
    ),
    (
        "alliance_genome_tool.py",
        "referenceCuries",
        "the literature about the gene -- 4,461 publications on the MGI record",
    ),
    (
        "alliance_genome_tool.py",
        "geneSecondaryIds",
        "retired accessions, which is how the older literature cites the gene",
    ),
    (
        "alliance_genome_tool.py",
        "relatedNotes",
        "the curator notes the model-organism database wrote about the gene",
    ),
    (
        "alliance_genome_tool.py",
        "predictedVariantConsequences",
        "the VEP impact and transcript consequence, which is the content of an allele record",
    ),
    (
        "alliance_genome_tool.py",
        "associatedPhenotype",
        "what is wrong with the mutant strain, beside a hasPhenotype boolean that said only that something is",
    ),
    (
        "alliance_genome_tool.py",
        '"stringency": r.get("stringencyFilter"),\n                    "subject_taxon_id"',
        "which stringency band an ortholog row met, for a call that takes a stringency",
    ),
    (
        "alliance_genome_tool.py",
        "conditionRelations",
        "the conditions a phenotype was observed under",
    ),
    (
        "alliance_genome_tool.py",
        "automatedGeneDescription",
        "what a search hit is known for, so hits can be ranked without a call each",
    ),
    # Round two: the families the catalogue-wide run ranked highest.
    (
        "epigenomics_tool.py",
        'item.get("sourceIds")',
        "which ENCODE experiments support a TF cluster, beside a sourceCount that said how many",
    ),
    (
        "epigenomics_tool.py",
        'feat.get("extended_start")',
        "the Regulatory Build's flanking bounds, a different overlap question from the core ones",
    ),
    (
        "monarch_v3_tool.py",
        "knowledge_level",
        "whether a Biolink association is a curated assertion or a prediction",
    ),
    (
        "monarch_v3_tool.py",
        "has_percentage",
        "how often a phenotype occurs in the disease, not merely that it has been seen",
    ),
    (
        "monarch_v3_tool.py",
        "mapping_justification",
        "whether a cross-ontology mapping was curated or produced by a string match",
    ),
    (
        "monarch_v3_tool.py",
        "causes_disease",
        "the diseases a gene causes, in the same response as its name",
    ),
    (
        "ebi_proteins_ext_tool.py",
        "predictions",
        "SIFT and PolyPhen, dropped from a variant tool that answered the position",
    ),
    (
        "ebi_proteins_ext_tool.py",
        "populationFrequencies",
        "how common the variant is, without which a clinical significance cannot be weighed",
    ),
    (
        "ebi_proteins_ext_tool.py",
        '"consequence_type": feature.get("consequenceType")',
        "what the variant does to the protein; present on all 3,662 features of P04637",
    ),
    (
        "ebi_proteins_ext_tool.py",
        "reviewStatus",
        "what separates a reviewed ClinVar assertion from one unreviewed submission",
    ),
    (
        "ebi_proteins_ext_tool.py",
        '"exons": [',
        "the exon coordinates, beside a num_exons that was the count of them",
    ),
    (
        "ebi_proteins_ext_tool.py",
        '"ligand": {',
        "what binds at a binding site, for a feature that named only the position",
    ),
    (
        "sgd_tool.py",
        'i.get("bait_hit")',
        "the direction SGD states; 83 of 180 rows are Hit-Bait and the labels were positional",
    ),
    (
        "sgd_tool.py",
        '(i.get("experiment") or {}).get("display_name")',
        "the experiment type, which was read from a key the API does not send",
    ),
    (
        "sgd_tool.py",
        '"is_reference_strain"',
        "which of 41 strains the returned sequence is, where the fallback was silent",
    ),
    (
        "sgd_tool.py",
        "alias_details",
        "what kind of alias each name is; a GenBank accession is not a gene synonym",
    ),
    (
        "sgd_tool.py",
        'a.get("sga_score")',
        "the quantitative strength of a genetic interaction and its p-value",
    ),
    (
        "mgnify_expanded_tool.py",
        '"rna_16s": attrs.get("rna-16s"),\n                    "rna_23s"',
        "the MIMAG criteria a MAG's quality is judged by, beside its completeness",
    ),
    (
        "mgnify_expanded_tool.py",
        "sample-metadata",
        "the submitter's own pH, temperature and depth, where the fixed fields are null",
    ),
    (
        "ctg_tool.py",
        '"countries": countries',
        "where a trial runs, which is what a trial search is filtered on",
    ),
    # Round three.
    (
        "graphql_tool.py",
        '"total_associated_targets": total_count',
        "the denominator: 918 targets with a score is 918 of 4,461, not of nothing",
    ),
    (
        "zooma_tool.py",
        '"derived_from": {',
        "the database that curated the mapping, where the tool reported its own inference step",
    ),
    (
        "zooma_tool.py",
        '"title": s.get("title")',
        "the name of each datasource, from a tool whose only job is to list them",
    ),
    (
        "oma_tool.py",
        'orth.get("entry_nr")',
        "the key OMA's own endpoints take, without which a result is a dead end",
    ),
    (
        "hpo_tool.py",
        "_hpo_medical_actions",
        "a phenotype's curated treatments, which no tool exposed while sitting in the response",
    ),
    (
        "hpo_tool.py",
        "also_in_this_response",
        "that the one request also answered 3,136 diseases and 14 medical actions",
    ),
    (
        "hpo_tool.py",
        'term.get("publicationReferences")',
        "what a term's definition rests on",
    ),
    (
        "ctg_tool.py",
        'ref.get("pmid")',
        "the trial's publications, for a search result that could not be followed",
    ),
    (
        "alliance_genome_tool.py",
        "predictionMethodsNotMatched",
        "the methods that did NOT support an ortholog call, which is what makes method_count mean anything",
    ),
    # Round four.
    (
        "genome_nexus_tool.py",
        'data.get("mutation_assessor")',
        "a predictor the call asks for in its own fields= parameter and then dropped",
    ),
    (
        "genome_nexus_tool.py",
        'tc.get("biotype")',
        "whether the consequence is on a coding transcript or one marked for decay",
    ),
    (
        "genome_nexus_tool.py",
        'item.get("missenseCount")',
        "what a hotspot's tumour count is made of; 897 missense and 0 truncating at BRAF V600",
    ),
    (
        "genome_nexus_tool.py",
        'data.get("exons")',
        "the exon structure, from the tool whose whole job is the canonical transcript",
    ),
    (
        "genome_nexus_tool.py",
        "transcriptConsequenceSummary",
        "the canonical summary, read before the list so the symbol is not whichever came first",
    ),
    (
        "disgenet_tool.py",
        'row.get("geneSymbol_keyword")',
        "the gene a variant sits in; a VDA row spells it differently and returned null",
    ),
    (
        "disgenet_tool.py",
        'row.get("mostSevereConsequences")',
        "what the variant does, from a variant-disease association tool",
    ),
    (
        "disgenet_tool.py",
        "alleleFreqExome",
        "how common the allele is; rs1801133's C677T is 32% and that bears on the association",
    ),
    (
        "disgenet_tool.py",
        'row.get("polyphen_score")',
        "the pathogenicity prediction on the same row as the rsID",
    ),
    (
        "epigraphdb_tool.py",
        'rel.get("action_type")',
        "whether the drug inhibits or activates; all 43 EGFR rows carry it and none of the CPIC fields",
    ),
    (
        "epigraphdb_tool.py",
        'pick("rg_intercept")',
        "the LDSC intercept that says whether an rg of 0.95 is sample overlap",
    ),
    (
        "epigraphdb_tool.py",
        'gs.get("pval")',
        "the p-value this tool takes pval_threshold to filter on and did not report",
    ),
    (
        "epigraphdb_tool.py",
        'assoc.get("id")',
        "the outcome trait each repurposing estimate was measured against",
    ),
    # Round five.
    (
        "glygen_tool.py",
        'raw.get("enzyme")',
        "the biosynthetic enzymes the class docstring names, which no GlyGen tool exposed",
    ),
    (
        "glygen_tool.py",
        'raw.get("residues")',
        "the structure residue by residue, where number_monosaccharides was all that was said",
    ),
    (
        "glygen_tool.py",
        'raw.get("glycation")',
        "glycation at a site, the one of the three PTM sections the site tool never read",
    ),
    (
        "glygen_tool.py",
        'raw.get("neighbors")',
        "the annotated sites around this one, with distance and direction",
    ),
    (
        "glygen_tool.py",
        "reported_n_glycosites",
        "the key a /protein/list row actually carries; the two that were read do not exist",
    ),
    (
        "glygen_tool.py",
        'v.get("glycoeffect")',
        "what an SNV does to the glycosylation, which is the question GlyGen answers",
    ),
    (
        "glygen_tool.py",
        'item.get("ec_number_list")',
        "the EC numbers of a protein a glycoprotein search returned 51 of",
    ),
    (
        "pubchem_tox_tool.py",
        "_reference_index",
        "who stated an LD50, which every statement points at and none of them carried",
    ),
    (
        "pubchem_tox_tool.py",
        "ExternalTableName",
        "PubChem answering that the data is in a table elsewhere, which read as no data",
    ),
    (
        "pubchem_tox_tool.py",
        "_statements_in_subtree",
        "the statements a summary topic counted, at the depth they actually sit",
    ),
    (
        "openfda_device_tool.py",
        "_mdr_texts",
        "what happened, from a MAUDE row that carried problem codes and no narrative",
    ),
    (
        "openfda_device_tool.py",
        "code_info",
        "which models and serial numbers a recall covers",
    ),
    (
        "openfda_device_tool.py",
        "mri_safety",
        "whether a device is safe near an MRI, which the UDI record states",
    ),
    (
        "openfda_device_tool.py",
        "_openfda_ids",
        "the clearance and establishment numbers the device endpoints take as input",
    ),
    (
        "openfda_device_tool.py",
        "supplement_number",
        "which PMA decision a row is, where one number covers the approval and every change",
    ),
    # Round six.
    (
        "mavedb_tool.py",
        "clinvarLinks",
        "the link from a ClinVar control to the measured score, read from a key that is not there",
    ),
    (
        "mavedb_tool.py",
        "def _publication",
        "the paper's title, journal, year and authors beside the PubMed number",
    ),
    (
        "mavedb_tool.py",
        "uniprotIdFromMappedMetadata",
        "the target's UniProt accession, which was read from a key a target sequence does not have",
    ),
    (
        "mavedb_tool.py",
        "scoreCalibrations",
        "the score ranges that map onto ACMG evidence strengths",
    ),
    (
        "mavedb_tool.py",
        "scoreDistribution",
        "the range and histogram the caller needs to pick a threshold",
    ),
    (
        "mavedb_tool.py",
        "def _keywords",
        "the controlled keywords an experiment is indexed under",
    ),
    (
        "wormbase_tool.py",
        "alleleSymbol",
        "which allele a phenotype belongs to; the annotation's subject is not the gene",
    ),
    (
        "wormbase_tool.py",
        "def _reference",
        "the PMID behind an annotation, where only Alliance's own curie came back",
    ),
    (
        "wormbase_tool.py",
        "phenotypesOrTraits",
        "the phenotype a genetic interaction was scored by, which is the result",
    ),
    (
        "wormbase_tool.py",
        "predictionMethodsNotCalled",
        "the methods that ran and did not call an ortholog",
    ),
    (
        "wormbase_tool.py",
        "def _perturbation",
        "which allele or RNAi a genetic interaction was measured with",
    ),
    (
        "wormbase_tool.py",
        "nb_annotations",
        "how many disease annotations the gene has, against a ribbon of all categories",
    ),
    (
        "wormbase_tool.py",
        "detectionMethod",
        "how an interaction was detected, without which the pair is not a result",
    ),
    (
        "usda_plants_tool.py",
        "def _plant_identity",
        "which plant a symbol resolved to, from a profile every one of these tools fetched",
    ),
    (
        "usda_plants_tool.py",
        'profile.get("Ancestors")',
        "the classification, nine ranks of it, from a plant profile tool",
    ),
    (
        "usda_plants_tool.py",
        'profile.get("MapCoordinates")',
        "where the plant occurs, where fips_distribution is null on most records",
    ),
    (
        "usda_plants_tool.py",
        'profile.get("AcceptedSymbol")',
        "where a symbol resolves when USDA names an accepted taxon separately",
    ),
    (
        "cancer_prognosis_tool.py",
        "_study_counts",
        "samples per modality, where max() of three of them was the whole answer",
    ),
    (
        "cancer_prognosis_tool.py",
        "referenceGenome",
        "whether a study's coordinates are hg19 or hg38",
    ),
    (
        "cancer_prognosis_tool.py",
        'p.get("datatype")',
        "whether expression values are Z-scores, which was being inferred from the profile id",
    ),
    (
        "fda_orange_book_tool.py",
        "def _identifiers",
        "the NDC and SPL codes an approval is joined to a claim or a label by",
    ),
    (
        "fda_orange_book_tool.py",
        "reference_standard",
        "which product generics are tested against, and which product a TE code is for",
    ),
    # Round nine.
    (
        "ncbi_datasets_tool.py",
        "_gene_ontology",
        "122 GO terms on a gene record, with their evidence codes and PMIDs",
    ),
    (
        "ncbi_datasets_tool.py",
        "genetic_code",
        "which translation tables a taxon uses, nuclear and mitochondrial",
    ),
    (
        "clingen_tool.py",
        'item.get("warnings")',
        "a curator's stated disagreement with ClinVar about a pathogenicity call",
    ),
    (
        "ewas_atlas_tool.py",
        "posToTss",
        "how far a CpG probe sits from a transcript's start site",
    ),
    (
        "pheweb_phewas_tool.py",
        'p.get("num_samples")',
        "the n behind a quantitative-trait association, where there are no cases to count",
    ),
    (
        "pheweb_phewas_tool.py",
        "resolved_variant",
        "what an rsID resolved to, from the Ensembl record the resolution fetched",
    ),
    (
        "efo_tool.py",
        "term_replaced_by",
        "what an obsolete term was replaced by, where the tool said only that it is obsolete",
    ),
    # Round ten.
    (
        "rgd_tool.py",
        'ann.get("objectSymbol")',
        "what an annotation is on, from 1,114 rows that named only the term",
    ),
    (
        "rgd_tool.py",
        'q.get("peakRgdId")',
        "the peak and flanking markers that define where a QTL is",
    ),
    (
        "rgd_tool.py",
        'r.get("diseases")',
        "the diseases a gene hit is associated with, which is why RGD is searched",
    ),
    (
        "rgd_strain_tool.py",
        'rec.get("lastStatus")',
        "whether a strain can still be obtained",
    ),
    (
        "impc_tool.py",
        'gene_data.get("allele_name"',
        "which alleles IMPC phenotyped, beside the phenotype status",
    ),
    (
        "progenetix_tool.py",
        "pathological_tnm_findings",
        "all three TNM findings, where the first label was reported as the staging",
    ),
    (
        "progenetix_tool.py",
        's.get("cohorts")',
        "which study a sample in a CNV search came from",
    ),
    (
        "metabolite_tool.py",
        'entry.get("mesh_chemical_id")',
        "which CTD chemical a metabolite name was matched to",
    ),
    (
        "metabolite_tool.py",
        "terms_tried",
        "which name variants were tried, so an empty answer is not read as no associations",
    ),
    # Round twelve.
    (
        "uniprot_tool.py",
        'entry.get("entryType")',
        "reviewed against unreviewed, the biggest quality distinction in UniProt",
    ),
    (
        "uniprot_ref_tool.py",
        "taxonLineage",
        "where a proteome's organism sits in the tree, 30 ranks of it",
    ),
    (
        "uniprot_ref_tool.py",
        'r.get("citations")',
        "the papers describing a proteome, with their 2,840 author names",
    ),
    (
        "quickgo_tool.py",
        "id_to_term",
        "what a GO term means, from the record the name backfill already fetched",
    ),
    (
        "reactome_content_tool.py",
        'entry.get("summation")',
        "the paragraph describing a pathway, answered for all 30 search hits",
    ),
    (
        "reactome_content_tool.py",
        "orthologousEvent",
        "the same reaction inferred in other species",
    ),
    (
        "pfam_tool.py",
        "entry_integrated",
        "the InterPro entry a Pfam family is integrated into",
    ),
    (
        "openfda_adv_tool.py",
        'openfda.get("rxcui")',
        "the RxNorm concept that resolves TYLENOL and acetaminophen to one drug",
    ),
    (
        "clingen_ar_tool.py",
        'ta.get("geneSymbol")',
        "the gene the allele is in, which the tool's own example promises",
    ),
    (
        "clingen_ar_tool.py",
        '"MANE"',
        "the MANE Select transcript, the representation the registry normalises to",
    ),
    (
        "clingen_ar_tool.py",
        '_ID_KEYS = ("rs", "alleleId", "variationId"',
        "the dbSNP rsID, read from `id`, a key the dbSNP record does not send",
    ),
    (
        "epmc_annotations_tool.py",
        '"tags": tags',
        "both ends of a relationship annotation, where only tags[0] was read",
    ),
    (
        "epmc_annotations_tool.py",
        'ann.get("section")',
        "whether a gene was mentioned in the Methods or in the Results",
    ),
    (
        "epmc_annotations_tool.py",
        'ann.get("provider")',
        "which text-mining pipeline made the claim",
    ),
    (
        "drugcentral_tool.py",
        'dc.get("pharmacology_class")',
        "the drug's FDA Established Pharmacologic Class, from a drug-information tool",
    ),
    (
        "drugcentral_tool.py",
        'rec.get("llr_threshold")',
        "the threshold an llr is a signal against; one without the other says nothing",
    ),
    (
        "drugcentral_tool.py",
        'u.get("swissprot_entry")',
        "the Swiss-Prot entry name of a target the tool exists to name",
    ),
    (
        "bgee_tool.py",
        'call.get("fdr")',
        "the FDR behind a present/absent expression call",
    ),
    (
        "bgee_tool.py",
        'match.get("match")',
        "which synonym a SYNONYM match matched",
    ),
    (
        "medlineplus_tool.py",
        '"db-key-list"',
        "the OMIM, NCBI Gene, GTR and ICD-10-CM codes for the page",
    ),
    (
        "medlineplus_tool.py",
        'gene_summary.get("gene-symbol"',
        "the gene symbol, where `name` is the protein name",
    ),
    (
        "ebi_proteins_features_tool.py",
        'f.get("ligand")',
        "what binds at a BINDING site, from the category whose name is 'binding sites'",
    ),
    (
        "ebi_proteins_features_tool.py",
        'f.get("ftId")',
        "the UniProt feature id a processed chain is cited by",
    ),
    (
        "chebi_tool.py",
        'struct_data.get("standard_inchi", None)',
        "the InChI, where only its hash was returned",
    ),
    (
        "chebi_tool.py",
        'raw.get("roles_classification")',
        "the role classification, which is half of what ChEBI is for",
    ),
    (
        "chebi_tool.py",
        'rec.get("accession_number")',
        "the CAS number and the registry, citation and xref accessions beside it",
    ),
    (
        "ols_tool.py",
        'item.get("exact_synonyms")',
        "the synonyms every OLS search hit carries",
    ),
    (
        "ols_tool.py",
        'alias="importsFrom"',
        "which ontologies an ontology depends on",
    ),
    (
        "ols_tool.py",
        '"is_obsolete": (term_data or {}).get("isObsolete")',
        "whether the term the similar ones are similar to has been retired",
    ),
    (
        "itis_tool.py",
        '_rows(data.get("synonymList"), "synonyms")',
        "the synonyms, which are the reason to consult a taxonomic authority",
    ),
    (
        "itis_tool.py",
        '_rows(data.get("acceptedNameList"), "acceptedNames")',
        "the name that replaced an invalid one, and the reason it was rejected",
    ),
    (
        "itis_tool.py",
        '"credibility_rating"',
        "the Taxonomic Work Group's verdict on the record",
    ),
    (
        "gbif_taxonomy_tool.py",
        '"kingdomKey"',
        "the rank keys, the handles for walking a tree the tool exists to walk",
    ),
    (
        "gbif_taxonomy_tool.py",
        '"issues"',
        "GBIF's own data-quality flags on the usage record",
    ),
    (
        "gbif_taxonomy_tool.py",
        'rec.get("preferred")',
        "which of a taxon's common names GBIF marks as the one to show",
    ),
    (
        "hubmap_tool.py",
        'person.get("orcid_id")',
        "the contributor ORCID, read from `orcid`, a key HuBMAP does not send",
    ),
    (
        "hubmap_tool.py",
        "organ_donor_data",
        "what the donor was -- age, sex, race -- at the end of a provenance chain",
    ),
    (
        "hubmap_tool.py",
        'org.get("laterality")',
        "which side a paired organ is, legible only inside the term string",
    ),
    (
        "rxclass_tool.py",
        'by_name.get("Relation")',
        "DIRECT against INDIRECT membership, which are not the same claim",
    ),
    (
        "ebi_proteins_coordinates_tool.py",
        'gc.get("feature")',
        "the 1,514 annotations per transcript the mapping response already carried",
    ),
    (
        "ebi_proteins_coordinates_tool.py",
        'genomic_loc.get("assemblyName")',
        "which assembly the genome positions are against",
    ),
    (
        "ebi_proteins_interactions_tool.py",
        'row.get("dbReference")',
        "the OMIM id of a disease the tool listed by name only",
    ),
    (
        "swissmodel_tool.py",
        's.get("ligand_chains")',
        "what is bound in the model, where the protein partners were reported",
    ),
    (
        "swissmodel_tool.py",
        's.get("oligo-state")',
        "whether the model is a monomer or an oligomer",
    ),
    (
        "hubmap_sample_tool.py",
        'metadata.get("living_donor_data")',
        "a living donor's attributes, which organ_donor_data does not hold",
    ),
    (
        "hubmap_sample_tool.py",
        'src.get("descendants")',
        "which datasets were made from the sample",
    ),
    (
        "nasa_osdr_tool.py",
        'metadata.get("study protocol description")',
        "the methods of a study whose tool promises its full metadata",
    ),
    (
        "nasa_osdr_tool.py",
        'source.get("Data Source Type")',
        "which repository a search row actually came from",
    ),
    (
        "uniprot_idmapping_tool.py",
        'item.get("to", False)',
        "whether a database can be mapped TO, where only FROM was reported",
    ),
    (
        "uniprot_idmapping_tool.py",
        'item.get("uriLink")',
        "how to resolve a mapped id, which is what mapping it was for",
    ),
    (
        "uniprot_idmapping_tool.py",
        '"unreviewed" not in entry_type.lower()',
        "Swiss-Prot against TrEMBL, tested on the string that is not a substring",
    ),
    (
        "uniprot_tool.py",
        '"unreviewed" not in entry_type.lower()',
        "the same test, where the substring form called every TrEMBL entry reviewed",
    ),
    (
        "gwas_sumstats_tool.py",
        'entry.get("summaryStatistics")',
        "whether a study has summary statistics, from a tool named after them",
    ),
    (
        "gwas_sumstats_tool.py",
        'entry.get("initialSampleDescription")',
        "the discovery sample, which is what a GWAS result means",
    ),
    (
        "ctg_tool.py",
        '_outcomes("secondaryOutcomes")',
        "the 39 secondary outcomes of a trial that reported 4 primary ones",
    ),
    (
        "ctg_tool.py",
        'item.get("armGroupLabels")',
        "which arms an intervention was given in",
    ),
    (
        "fooddata_central_tool.py",
        'n.get("derivationDescription")',
        "whether a nutrient value was measured or calculated",
    ),
    (
        "cellxgene_discovery_tool.py",
        'collection.get("publisher_metadata")',
        "the paper a collection belongs to, so it can be cited",
    ),
    (
        "cellxgene_discovery_tool.py",
        "def _ontology_terms",
        "which tissues a collection covers, which its sibling handler reads",
    ),
    (
        "nci_evs_tool.py",
        'c.get("conceptStatus")',
        "whether a terminology concept has been retired",
    ),
    (
        "nextstrain_tool.py",
        "def _coloring_values",
        "the values a build covers for a coloring, where only the key was given",
    ),
    (
        "orcid_tool.py",
        's.get("external-ids")',
        "a review's own external ids, where only its group's were read",
    ),
    (
        "orcid_tool.py",
        "def _source_name",
        "who deposited an ORCID assertion",
    ),
    (
        "fda_orange_book_tool.py",
        "_submission_summary(result.get(\"submissions\"))",
        "when an application was approved, in a row that answers whether a generic exists",
    ),
    (
        "expression_atlas_tool.py",
        'exp.get("experimentalFactors")',
        "which variables a baseline experiment measured across",
    ),
    (
        "hubmap_sample_tool.py",
        "def _donor_demographic_codes",
        "the SNOMED codes behind a donor's attributes",
    ),
    (
        "ddbj_tool.py",
        "def _xref_type_counts",
        "what a cross-reference count was counting",
    ),
    (
        "timer_tool.py",
        "def _get_study_sample_count",
        "how many samples the study has, against the 100 the estimate used",
    ),
    (
        "open_genes_tool.py",
        "def _evidence_digest",
        "what 57 longevity-association records say, where only '57' was reported",
    ),
    (
        "cath_tool.py",
        "def _go_terms",
        "a domain's GO annotations, which its sibling handler returns",
    ),
    (
        "cath_tool.py",
        'data.get("pdb_segments")',
        "the residue ranges that define the domain",
    ),
    (
        "humanbase_tool.py",
        "def _top_evidence_datasets",
        "which experiments support an interaction, where only a count was printed",
    ),
    (
        "cbioportal_tool.py",
        '"alteration_type": profile.get("molecularAlterationType")',
        "which molecular profile the mutations came from",
    ),
    (
        "orphanet_tool.py",
        'gene_info.get("Synonym")',
        "a gene's other symbols, which is how the answer is matched elsewhere",
    ),
    (
        "uniprot_ref_tool.py",
        '"taxon_lineage_nodes"',
        "the taxon ids of a lineage returned as bare names",
    ),
    (
        "ctg_tool.py",
        "def _results_summary",
        "that a trial has posted results at all, from a tool promising full details",
    ),
    (
        "ucsc_cell_browser_tool.py",
        'dataset.get("sampleCount")',
        "how many cells a single-cell dataset has",
    ),
    (
        "ucsc_cell_browser_tool.py",
        'dataset.get("hasFiles")',
        "which files exist for a dataset, so it can be fetched rather than browsed",
    ),
    (
        "screen_ccre_tool.py",
        '"length": length,',
        "a regulatory element's own width, used to compute `end` and dropped",
    ),
    (
        "sgd_tool.py",
        'entry.get("display_name")',
        "the GO Slim TERM, where the row carried the name of the slim set",
    ),
    (
        "sgd_tool.py",
        "def _phenotype_summary",
        "the phenotypes themselves, beside the count of assay categories",
    ),
    (
        "genome_nexus_tool.py",
        'canonical.get("hgvspShort")',
        "which hotspot, for an answer that said only that there is one",
    ),
    (
        "ensembl_info_tool.py",
        's.get("groups")',
        "which Ensembl data sets exist for a species",
    ),
    (
        "mirna_tool.py",
        'pub.get("pub_id")',
        "the source record id that tells two RNAcentral records for one PMID apart, "
        "which the tool's own warning asks the caller to expect",
    ),
    (
        "dandi_tool.py",
        '"version_is_published"',
        "which version the name, asset count and size describe, when the sibling "
        "tools read a different one",
    ),
    (
        "magicapp_tool.py",
        '"institutionShortName"',
        "the organisation that published the guideline, one of the five fields "
        "the query is matched against",
    ),
    (
        "magicapp_tool.py",
        '"publishLastSearchDate"',
        "when the evidence was last searched, the currency of a living guideline "
        "whose publishDate can be a decade older",
    ),
    (
        "pubchem_bioassay_tool.py",
        'summary.get("Protocol")',
        "the assay protocol, which reached neither the search nor the summary tool",
    ),
    (
        "pubchem_bioassay_tool.py",
        '_counts(summary, "CID")',
        "how many compounds the screen tested and how many were active, which is "
        "what tells a screen worth opening from an empty one",
    ),
    (
        "go_api_tool.py",
        'association.get("evidence_types")',
        "the evidence code's label, under the key the API actually sends",
    ),
    (
        "go_api_tool.py",
        'association.get("publications")',
        "a GO annotation's references, under the key the API actually sends",
    ),
    (
        "go_api_tool.py",
        "def _is_negated",
        "NOT annotations, which were returned as genes having the function",
    ),
    (
        "interpro_entry_tool.py",
        '"match_locations"',
        "where on the protein the domain matches, for a tool that answers which "
        "domains a protein has",
    ),
    (
        "harmonizome_tool.py",
        'g.get("synonyms")',
        "the gene's other symbols, in a tool that resolves by exact symbol",
    ),
    (
        "dbsnp_tool.py",
        '"studies_unparsed"',
        "that a study's frequency string did not parse, rather than dropping it",
    ),
    (
        "alliance_genome_tool.py",
        'r.get("geneToGeneParalogy")',
        "the branch a paralogy row arrives in, which was read as an all-null ortholog",
    ),
    (
        "alliance_genome_tool.py",
        "para.get(\"rank\")",
        "how close a paralog is, in a list ordered by it",
    ),
    (
        "compound_drug_profile_tool.py",
        'synonym.get("syn_type")',
        "which of a drug's 80 synonyms is a brand name and which a lab code",
    ),
    (
        "membrane_topology_tool.py",
        'o.get("subunit_segments")',
        "how many times the subunit crosses the bilayer, in a membrane-topology tool",
    ),
    (
        "membrane_topology_tool.py",
        'o.get("comments")',
        "the curator's prose, in a row whose `description` is null on every record",
    ),
    (
        "membrane_topology_tool.py",
        'o.get("species_name_cache")',
        "which organism the solved structure came from",
    ),
    (
        "mcsa_tool.py",
        'first.get("auth_resid")',
        "the PDB numbering of a catalytic residue, which is the number the "
        "literature and a mutation name use",
    ),
    (
        "mcsa_tool.py",
        'role.get("function_type")',
        "whether a catalytic residue is a reactant, an interaction partner or "
        "a spectator",
    ),
    (
        "mcsa_tool.py",
        "def _mechanisms",
        "the curated mechanism the atlas exists for, and its references",
    ),
    (
        "mcsa_tool.py",
        'compound.get("chebi_id")',
        "the reaction's substrates and products, promised by the tool's own "
        "description",
    ),
    (
        "hca_tool.py",
        '"genusSpecies"',
        "the species of a project in a catalogue that holds mouse as well as "
        "human",
    ),
    (
        "hca_tool.py",
        '"libraryConstructionApproach"',
        "which single-cell assay a single-cell project used",
    ),
    (
        "hca_tool.py",
        'f.get("sha256")',
        "the checksum that makes a download manifest verifiable",
    ),
    (
        "ndex_tool.py",
        "def _cx_attributes",
        "the per-node and per-edge measurements that make a network a finding "
        "rather than a drawing",
    ),
    (
        "ndex_tool.py",
        "edgeAttributes",
        "2,222 edge attributes on a 118-edge network, none of which reached "
        "the caller",
    ),
    (
        "interpro_ext_tool.py",
        "def _match_locations",
        "where on each protein the requested domain sits, which is what "
        "'contains this domain' means",
    ),
    (
        "interpro_ext_tool.py",
        'meta.get("gene")',
        "the gene name of a protein a domain search returned",
    ),
    (
        "monarch_v3_tool.py",
        "def _search_row",
        "one row builder for the one /search endpoint both handlers call, "
        "instead of six fields in one and fifteen in the other",
    ),
    (
        "pdbe_kb_tool.py",
        'residue.get("startCode")',
        "which amino acid the binding-site residue is, in a tool that promises "
        "binding site residues",
    ),
    (
        "pdbe_kb_tool.py",
        "def _residue_row",
        "one residue builder for the ligand and interface faces of one "
        "endpoint family",
    ),
    (
        "pdbe_kb_tool.py",
        'additional.get("scaffoldId")',
        "what the bound ligand actually is, as SMILES",
    ),
    (
        "depmap_tool.py",
        '"data_available"',
        "whether a cell line has CRISPR knockout data at all, for a tool whose "
        "description offers it for target validation",
    ),
    (
        "depmap_tool.py",
        'attributes.get("mutations_per_mb")',
        "the line's tumour mutational burden",
    ),
    (
        "inaturalist_tool.py",
        "def _conservation_status",
        "the authority behind a conservation status: 'G4' is a NatureServe "
        "rank, not an IUCN category",
    ),
    (
        "inaturalist_tool.py",
        'listing.get("establishment_means")',
        "whether the taxon is native or introduced where it is listed",
    ),
    (
        "three_d_beacons_tool.py",
        'sm.get("model_format")',
        "the format of the file at the download URL the tool promises",
    ),
    (
        "three_d_beacons_tool.py",
        "def _entities",
        "which chains and bound ligands a structure holds, for a list of 375 "
        "of them",
    ),
    (
        "restful_tool.py",
        'disease.get("subject")',
        "the MONDO curie the differential should be intersected on, rather "
        "than the disease's label",
    ),
    (
        "finngen_tool.py",
        'record.get("gc_lambda")',
        "the genomic-control factor that says whether a GWAS is usable, on all "
        "2,470 phenotypes and returned by only one of the two handlers",
    ),
    (
        "finngen_tool.py",
        "def _phenotype_row",
        "one phenotype row for the list and the lookup, which read the same "
        "upstream record shape and reported different fields",
    ),
    (
        "fda_gsrs_tool.py",
        'c.get("comments")',
        "the ATC classification path a WHO-ATC code stands for",
    ),
    (
        "fda_gsrs_tool.py",
        "def _reference_index",
        "the citations a name's reference uuids point at, which the module's "
        "own docstring promises as regulatory references",
    ),
    (
        "alliance_genome_tool.py",
        'annotation.get("phenotypeTerms")',
        "the Mammalian Phenotype term and its id, which MGI_get_phenotypes "
        "names in its own description",
    ),
    (
        "alliance_genome_tool.py",
        "def _annotation_facet",
        "the relation, the data provider and the annotated genotype, none of "
        "which reached the caller",
    ),
    (
        "nih_dsld_tool.py",
        "def _other_ingredients",
        "the inactive ingredients, which are half of the 'every ingredient' "
        "the description promises",
    ),
    (
        "nih_dsld_tool.py",
        'payload.get("percentDvFootnote")',
        "what the percent daily values the tool already returns are a "
        "percentage of",
    ),
    (
        "pgs_catalog_tool.py",
        't.get("child_associated_pgs_ids")',
        "8 polygenic scores that no other call this tool makes can reach",
    ),
    (
        "pgs_catalog_tool.py",
        't.get("trait_synonyms")',
        "why a trait row matched, when the query is a synonym of the label",
    ),
    (
        "alliance_genome_tool.py",
        "def _evidence_codes",
        "the ECO curie and the three-letter abbreviation an evidence code is "
        "cited by, beside the prose name the row kept",
    ),
    (
        "nci_thesaurus_tool.py",
        's.get("typeCode")',
        "which of seventeen synonyms is NCIt's own preferred name, when ten "
        "of them are a source terminology's PT",
    ),
    (
        "igsr_tool.py",
        "def _data_collections",
        "what data exists for a population - alignments, variants, the "
        "sequencing behind them and the reuse policy",
    ),
    (
        "interpro_domain_arch_tool.py",
        'fragment.get("auth_start")',
        "the PDB author numbering of a domain inside a structure, which is "
        "the numbering a paper uses",
    ),
    (
        "ndex_tool.py",
        "def _network_properties",
        "the organism, disease, tissue, method and licence a network search "
        "is picked on",
    ),
    (
        "genebe_tool.py",
        '"clinvar_submissions_summary"',
        "the submissions behind a ClinVar conflict: BRAF V600E is "
        "P:3 LP:1 US:5 O:1, and the row reported the conflict alone",
    ),
    (
        "genebe_tool.py",
        "def _consequences",
        "which of 43 annotated transcripts the classification is on, and "
        "which of them is MANE Select",
    ),
    (
        "interpro_domain_arch_tool.py",
        'p.get("source_database")',
        "whether the protein whose architecture this is reviewed or "
        "unreviewed, which both sibling endpoints already report",
    ),
    (
        "nasa_osdr_tool.py",
        '"Study Assay Technology Platform"',
        "the platform the assay ran on, which is often the only one of the "
        "three assay fields populated",
    ),
    (
        "nasa_osdr_tool.py",
        'source.get("Study Description")',
        "what each study was, in a search whose rows a caller has to choose "
        "between",
    ),
    (
        "smartapi_tool.py",
        'server.get("x-maturity")',
        "whether the url the tool hands over is the production server or the "
        "development one",
    ),
    (
        "smartapi_tool.py",
        "def _base_url",
        "the production server, where servers[0] was a development url",
    ),
    (
        "nci_thesaurus_tool.py",
        'row.get("source")',
        "which body wrote a concept's definition, where four bodies wrote one "
        "and the row returned the first with no source",
    ),
    (
        "alliance_genome_tool.py",
        'r.get("uberonTermIds")',
        "the anatomy ontology ids behind an expression annotation's free text",
    ),
    (
        "alliance_genome_tool.py",
        "def _expression_pattern",
        "the species-specific anatomy curie, which is not among the UBERON "
        "slim ids",
    ),
    (
        "proteins_api_tool.py",
        "PROTEOMICS_DATABASES",
        "the pointers to the mass-spectrometry evidence the tool's own "
        "description promises",
    ),
    (
        "uniprot_taxonomy_tool.py",
        'item.get("otherNames")',
        "the synonyms a taxonomy search matched on, which the per-taxon "
        "lookup beside it already returned",
    ),
    (
        "ensembl_info_tool.py",
        "OTHER_REGIONS_PER_ASSEMBLY",
        "the 169 scaffolds of GRCh38, which no tool in the family returned",
    ),
    (
        "dbgap_tool.py",
        "def _concept_codes",
        "the MeSH and UMLS codes for a study's condition, where ten free-text "
        "synonyms were returned and no identifier",
    ),
    (
        "clinvar_tool.py",
        'gene.get("geneid")',
        "which genes a pathogenic deletion covers, for a region search that "
        "reported only its span",
    ),
    (
        "sgd_tool.py",
        # Not a bare `p.get("note")`: sgd_tool.py already contained
        # `prop.get("note")` in two other handlers, which contains it.
        '"note": p.get("note")',
        "the curator's note behind a phenotype call, where the qualitative "
        "verdict was returned without the measurement that produced it",
    ),
    (
        "cellosaurus_tool.py",
        "def _cell_line_publications",
        "the publications a cell line's reference-list points at, where the "
        "pointers were returned and the records they point at dropped",
    ),
    (
        "inaturalist_tool.py",
        'photo.get("license_code")',
        "the licence a photo may be reused under, for a tool that handed "
        "over the photo's URL alone",
    ),
    (
        "inaturalist_tool.py",
        'photo.get("attribution")',
        "the attribution line that licence requires",
    ),
    (
        "inaturalist_tool.py",
        'r.get("ancestor_ids")',
        "the lineage that separates two taxa sharing a common name, for a "
        "search that returned the name and the rank alone",
    ),
    (
        "disprot_tool.py",
        "def _statements",
        "the sentence from the paper a disorder annotation rests on, where "
        "the term name and the evidence code were returned without it",
    ),
    (
        "disprot_tool.py",
        "def _partners",
        "what a region annotated `protein binding` binds",
    ),
    (
        "disprot_tool.py",
        'region.get("reference_id")',
        "the PubMed id of the paper behind each annotation",
    ),
    (
        "uniref_tool.py",
        "def _member",
        "the 253 members of a 254-member cluster, where only the "
        "representative was returned",
    ),
    (
        "gxa_tool.py",
        "def _column",
        "an experiment's conditions and the factor each varies, reported as "
        "a count by the one tool whose description promises factor "
        "information",
    ),
    (
        "disease_ontology_tool.py",
        '_validated_list(\n                            parent_data, "xrefs"',
        "the vocabulary mappings on a parent term, from a record the handler "
        "had already fetched to read its name",
    ),
    (
        "gmrepo_tool.py",
        "def _dblinks",
        "a species' links to other resources, which GMrepo answers as a JSON "
        "string",
    ),
    (
        "gmrepo_tool.py",
        'sp.get("ismarker")',
        "whether GMrepo treats the species as a phenotype marker",
    ),
    (
        "ctg_tool.py",
        "**_results_summary(s),",
        "whether a trial in a search result has posted results, from a reply "
        "that carried the whole results section",
    ),
    (
        "ebi_proteins_coordinates_tool.py",
        'feature.get("evidence") or feature.get("evidences")',
        "the ECO codes and publications behind an annotation, where the "
        "wrapper read only the plural key this endpoint never sends",
    ),
    (
        "ebi_proteins_coordinates_tool.py",
        '"nucleotide_id": loc.get("nucleotideId")',
        "the genomic sequence the coordinates are on, reported by the "
        "sibling handler and not by this one",
    ),
    (
        "uniref_tool.py",
        "def _go_terms",
        "a UniRef cluster's GO annotations, which no UniRef tool returned "
        "from either endpoint",
    ),
    (
        "uniref_tool.py",
        'common_taxon.get("taxonId")',
        "the taxon id beside the common taxon's name in the search row",
    ),
    (
        "disprot_tool.py",
        "def _gene_names",
        "every gene name on an entry, where both handlers took genes[0]",
    ),
    (
        "gxa_tool.py",
        'exp.get("kingdom")',
        "which kingdom an experiment is from, on all 4562 of them",
    ),
    (
        "europepmc_annotations_tool.py",
        "def _annotation_row",
        "the section, provider and frequency of an annotation, which say "
        "whether the term was in the paper's argument or in a supplementary "
        "spreadsheet",
    ),
    (
        "unichem_tool.py",
        's.get("srcLastUpdated")',
        "when a UniChem source last changed, read until now from a key the "
        "API does not send",
    ),
    (
        "unichem_tool.py",
        's.get("baseIdUrl")',
        "the URL prefix that turns a compound id into its record page",
    ),
    (
        "lincs_tool.py",
        "def _signature_file",
        "the URL, name and checksum of the signature file, for a search that "
        "described signatures a caller could not fetch",
    ),
    (
        "hpo_tool.py",
        'item.get("status")',
        "OFFICIAL or CANDIDATE: whether HPO stands behind a translated label or is only proposing it",
    ),
    (
        "membrane_topology_tool.py",
        'o.get("verification")',
        "OPM's own statement of whether the computed membrane placement was checked against experiment",
    ),
    (
        "membrane_topology_tool.py",
        'o.get("structure_subunits_count")',
        "how many subunits were positioned in the bilayer; 339 of 395 records sampled carry it",
    ),
    (
        "membrane_topology_tool.py",
        '"opm_id": o.get("id")',
        "OPM's primary key, the only safe way back to the full record",
    ),
    (
        "cms_open_payments_tool.py",
        "covered_recipient_profile_id",
        "CMS's stable recipient key, which joins a recipient's payments across program years",
    ),
    (
        "harmonizome_tool.py",
        'gs.get("href")',
        "the only path that fetches a gene set's genes; a dataset naming 5218 of them had no way to retrieve one",
    ),
    (
        "harmonizome_tool.py",
        'data.get("resource")',
        "which database the harmonized data came from, e.g. the Comparative Toxicogenomics Database",
    ),
    (
        "pgs_catalog_tool.py",
        'body.get("license")',
        "the terms under which the scoring file the tool links to may be reused",
    ),
    (
        "pgs_catalog_tool.py",
        '"ftp_harmonized_scoring_files"',
        "the GRCh37/GRCh38 files, as against the author's original build, which is what applying a score needs",
    ),
    (
        "pgs_catalog_tool.py",
        'body.get("samples_variants")',
        "the GWAS the score's variants were discovered in, with its ancestry; distinct from samples_training",
    ),
    (
        "pgs_catalog_tool.py",
        'body.get("matches_publication")',
        "whether the Catalog's own curation matches the paper it cites",
    ),
    (
        "pdbtm_tool.py",
        'payload.get("model_coordinates_url")',
        "the membrane-positioned coordinates the classification was computed from",
    ),
    (
        "pdbtm_tool.py",
        'site.get("label")',
        "the region legend without which PDBTM's per-residue site ids mean nothing",
    ),
    (
        "alliance_genome_tool.py",
        'data.get("crossReferenceLinkUrls")',
        "the mappings to MESH, UMLS, ICD9/10 and SNOMED, which are how a disease term joins anything else",
    ),
    (
        "alliance_genome_tool.py",
        'data.get("sourceReferenceLinkUrls")',
        "where RGD, MGI, ZFIN, FlyBase, WormBase and SGD record their annotations for the disease",
    ),
    (
        "alliance_genome_tool.py",
        'data.get("parentClosureIDs")',
        "the term's ancestors; the wrapper returned a disease ontology term with no position in the ontology",
    ),
    (
        "allen_cell_types_tool.py",
        'r.get("structure__layer")',
        "the cortical layer, without which a pyramidal neuron's cell type is not determined",
    ),
    (
        "allen_cell_types_tool.py",
        'r.get("ef__vrest")',
        "resting membrane potential, in a tool whose description promises electrophysiology",
    ),
    (
        "allen_cell_types_tool.py",
        'r.get("ef__threshold_i_long_square")',
        "rheobase: the minimum current that makes the cell fire",
    ),
    (
        "allen_cell_types_tool.py",
        'r.get("tag__dendrite_type")',
        "spiny or aspiny, the standard morphological proxy for excitatory versus inhibitory",
    ),
    (
        "allen_cell_types_tool.py",
        'r.get("donor__id")',
        "which brain each neuron came from; without it two cells from one donor look like two donors",
    ),
    (
        "mirna_tool.py",
        'acc.get("malacards_diseases")',
        "the diseases a MalaCards cross-reference names - 364 for hsa-miR-21-5p, of which the caller saw none",
    ),
    (
        "mirna_tool.py",
        '"citations_url": acc.get("citations")',
        "RNAcentral's citations key holds a URL, not a count, so the field has to be named for what it is",
    ),
    (
        "mirna_tool.py",
        '"last_seen": xref.get("last_seen")',
        "when the mapping was last confirmed; a stale cross-reference is not the same as a current one",
    ),
    (
        "classyfire_tool.py",
        'node.get("chemont_id")',
        "the ChemOnt identifier that makes a classification citable; the wrapper kept only the term's name",
    ),
    (
        "classyfire_tool.py",
        'rec.get("alternative_parents")',
        "ClassyFire's other valid classifications - aspirin is also a phenol ester and a benzoic acid",
    ),
    (
        "classyfire_tool.py",
        'rec.get("external_descriptors")',
        "the curated source-database annotations, carrying CHEBI:15365 for aspirin: the join back out of ChemOnt",
    ),
    (
        "classyfire_tool.py",
        'rec.get("classification_version")',
        "which ChemOnt release produced the classification, without which it cannot be reproduced",
    ),
]


@pytest.mark.parametrize(
    "module, key, why",
    UPSTREAM_KEYS,
    ids=[
        f"{m.removesuffix('.py')}:{k.split(chr(34))[1] if chr(34) in k else k}"[:60]
        for m, k, _ in UPSTREAM_KEYS
    ],
)
def test_the_wrapper_reads_the_field_the_api_answered(module, key, why):
    """Five of these anchors are the whole read expression, not the bare name.

    `samples`, `keywords`, `link`, `properties` and `level_name` each already
    occurred in their module before the fix -- in a docstring, in a sibling
    handler, as `reference_link` -- so a bare substring would have passed
    against the unfixed file and guarded nothing.
    """
    assert key in _source(module), (
        f"{module} does not read upstream `{key}`, which is {why}. "
        "Measured against the live API: the upstream answers it and the "
        "caller never sees it."
    )


# (tool, output field the schema must declare)
DECLARED = [
    ("Reactome_get_interactor", "isInferred"),
    ("Reactome_get_interactor", "reviewStatus"),
    ("GBIF_suggest_species", "nubKey"),
    ("Figshare_get_article", "is_embargoed"),
    ("Figshare_get_article", "is_metadata_record"),
    ("Figshare_get_article", "resource_doi"),
    ("openalex_search_works", "is_retracted"),
    ("openalex_search_works", "authorships"),
    ("openalex_search_works", "best_oa_location"),
    ("openalex_search_works", "referenced_works"),
    ("Nominatim_geocode", "licence"),
    ("Nominatim_geocode", "osm_id"),
    ("Nominatim_reverse_geocode", "osm_type"),
    ("umls_get_concept_details", "semanticTypes"),
    ("umls_get_concept_details", "suppressible"),
    ("umls_get_concept_details", "definitions"),
    ("SpliceAI_get_max_delta", "max_delta_effect"),
    ("SpliceAI_get_max_delta", "delta_by_effect"),
    ("SpliceAI_predict_splice", "max_delta_offset"),
    ("ClassyFire_classify_by_inchikey", "taxonomy"),
    ("ClassyFire_classify_by_inchikey", "alternative_parents"),
    ("ClassyFire_classify_by_inchikey", "external_descriptors"),
    ("ClassyFire_classify_by_inchikey", "classification_version"),
    ("miRBase_get_mirna_xrefs", "diseases"),
    ("miRBase_get_mirna_xrefs", "disease_count"),
    ("miRBase_get_mirna_xrefs", "citations_url"),
    ("Alliance_get_disease", "cross_references"),
    ("Alliance_get_disease", "source_links"),
    ("Alliance_get_disease", "ancestor_ids"),
    ("AllenCellTypes_search_specimens", "cortical_layer"),
    ("AllenCellTypes_search_specimens", "resting_potential_mv"),
    ("AllenCellTypes_search_specimens", "rheobase_pa"),
    ("AllenCellTypes_search_specimens", "dendrite_type"),
    ("AllenCellTypes_search_specimens", "donor_id"),
    ("Harmonizome_get_dataset", "source_resource"),
    ("PGSCatalog_get_score", "license"),
    ("PGSCatalog_get_score", "samples_variants"),
    ("PGSCatalog_get_score", "harmonized_scoring_files"),
    ("PGSCatalog_get_score", "matches_publication"),
    ("PDBTM_get_topology", "topology_segments"),
    ("PDBTM_get_topology", "model_coordinates_url"),
    ("PDBTM_get_topology", "residues_by_region"),
    ("OPM_search_structures", "opm_id"),
    ("OPM_search_structures", "verification"),
    ("OPM_search_structures", "subunits_positioned"),
    ("HPO_get_term", "translations_truncated"),
    ("HPO_get_term_hierarchy", "translation_count"),
    ("CMSOpenPayments_search_payments", "recipient_profile_id"),
    ("CMSOpenPayments_search_payments", "change_type"),
    ("EuroPMCAnnot_get_annotations_by_type", "provider"),
    ("EuroPMCAnnot_get_article_annotations", "frequency"),
    ("UniChem_list_sources", "base_id_url"),
    ("UniChem_list_sources", "last_checked"),
    ("LINCS_search_signatures", "data_file"),
    ("LINCS_search_signatures", "cmap_id"),
    ("ClinicalTrials_search_by_intervention", "has_results"),
    ("ClinicalTrials_search_studies", "results_summary"),
    ("ClinicalTrials_search_by_sponsor", "results_section_tools"),
    ("EBIProteins_get_proteins_by_genomic_loc", "nucleotide_id"),
    ("UniRef_search_clusters", "go_terms"),
    ("UniRef_search_clusters", "common_taxon_id"),
    ("UniRef_get_cluster", "go_terms"),
    ("DisProt_search", "gene_names"),
    ("DisProt_get_entry", "gene_count"),
    ("GxA_list_experiments", "kingdom"),
    ("DiseaseOntology_get_parents", "cross_references"),
    ("DiseaseOntology_get_parents", "synonyms"),
    ("GMrepo_search_species", "is_marker"),
    ("GMrepo_search_species", "database_links"),
    ("DisProt_get_entry", "statements"),
    ("DisProt_get_entry", "interaction_partners"),
    ("DisProt_get_entry", "evidence_code_id"),
    ("DisProt_get_entry", "reference_source"),
    ("UniRef_get_cluster", "members"),
    ("UniRef_get_cluster", "members_truncated"),
    ("GxA_get_experiment_info", "conditions"),
    ("GxA_get_experiment_info", "property_type"),
    ("SGD_get_phenotypes", "note"),
    ("SGD_get_phenotypes", "experiment_note"),
    ("cellosaurus_get_cell_line_info", "publications"),
    ("cellosaurus_get_cell_line_info", "publication_count"),
    ("iNaturalist_search_taxa", "ancestor_ids"),
    ("iNaturalist_search_taxa", "iconic_taxon_id"),
    ("iNaturalist_search_observations", "photos"),
    ("iNaturalist_search_observations", "license_code"),
    ("gProfiler_enrichment", "effective_domain_size"),
    ("gProfiler_enrichment", "intersection_genes"),
    ("GxA_get_experiment_expression", "expression_unit"),
    ("GEO_search_chipseq_datasets", "samples"),
    ("GEO_search_chipseq_datasets", "samples_truncated"),
    ("GEO_get_dataset_details", "samples"),
    ("OrthoDB_search_groups", "level_name"),
    ("OrthoDB_search_groups", "species_count"),
    ("FlyBase_get_gene_interactions", "subject_role"),
    ("FlyBase_get_gene_interactions", "references"),
    ("EBIProteins_get_hpp_peptides", "support"),
    ("MaveDB_get_gnomad_variants", "faf95_max"),
    ("MaveDB_get_gnomad_variants", "score_set_variants"),
    ("DisGeNET_search_gene", "disease_vocabularies"),
    ("DisGeNET_search_gene", "n_clinical_trials"),
    ("ComplexPortal_get_complex", "linked_features"),
    ("ComplexPortal_get_complex", "bio_role"),
    ("DOAJ_search_articles", "subjects"),
    ("DOAJ_search_articles", "author_affiliations"),
    ("Planteome_search_annotations", "assigned_by"),
    ("ExpressionAtlas_get_experiment", "assay_groups"),
    ("UniProtTaxonomy_get_taxon", "other_names"),
    ("MediaDive_search_media", "link"),
    ("IDR_search_images", "location"),
    ("Synapse_list_children", "benefactor_id"),
    # Round four.
    ("GenomeNexus_annotate_variant", "mutation_assessor"),
    ("GenomeNexus_annotate_variant", "biotype"),
    ("GenomeNexus_annotate_variant", "protein_start"),
    ("GenomeNexus_get_canonical_transcript", "exons"),
    ("GenomeNexus_get_canonical_transcript", "utrs"),
    ("GenomeNexus_get_cancer_hotspots", "missenseCount"),
    ("DisGeNET_get_vda", "most_severe_consequence"),
    ("DisGeNET_get_vda", "allele_frequencies"),
    ("DisGeNET_get_vda", "polyphen_score"),
    ("DisGeNET_get_vda", "gene_symbols"),
    ("DisGeNET_get_disease_genes", "disease_name"),
    ("DisGeNET_get_disease_genes", "score_breakdown"),
    ("DisGeNET_get_disease_genes", "year_first"),
    ("DisGeNET_get_gda", "gene_protein_classes"),
    ("DisGeNET_get_gda", "disease_inheritance"),
    ("EpiGraphDB_get_gene_drug_associations", "action_type"),
    ("EpiGraphDB_get_genetic_correlations", "rg_intercept"),
    ("EpiGraphDB_get_genetic_correlations", "h2_se"),
    ("EpiGraphDB_get_drugs_for_trait", "evidence"),
    ("EpiGraphDB_get_drugs_for_trait", "exposure_trait_id"),
    ("EpiGraphDB_get_literature_evidence", "pval"),
    # Round five.
    ("GlyGen_get_glycan", "enzymes"),
    ("GlyGen_get_glycan", "residues"),
    ("GlyGen_get_glycan", "biosynthesis_steps"),
    ("GlyGen_get_glycan", "publications"),
    ("GlyGen_get_glycoprotein", "diseases"),
    ("GlyGen_get_glycoprotein", "snvs"),
    ("GlyGen_get_glycoprotein", "glycoeffect"),
    ("GlyGen_get_glycoprotein", "pathways"),
    ("GlyGen_get_site", "glycation"),
    ("GlyGen_get_site", "neighbors"),
    ("GlyGen_get_site", "protein_name"),
    ("GlyGen_search_glycoproteins", "n_linked_site_count"),
    ("GlyGen_search_glycoproteins", "ec_numbers"),
    ("PubChemTox_get_toxicity_values", "source_name"),
    ("PubChemTox_get_toxicity_values", "license_note"),
    ("PubChemTox_get_carcinogen_classification", "source_url"),
    ("PubChemTox_get_acute_effects", "effect_truncated"),
    ("PubChemTox_get_toxicity_summary", "statements"),
    ("OpenFDADevice_search_adverse_events", "narratives"),
    ("OpenFDADevice_search_adverse_events", "devices"),
    ("OpenFDADevice_search_adverse_events", "report_number"),
    ("OpenFDADevice_search_recalls", "code_info"),
    ("OpenFDADevice_search_recalls", "identifiers"),
    ("OpenFDADevice_search_udi", "mri_safety"),
    ("OpenFDADevice_search_udi", "is_labeled_as_nrl"),
    ("OpenFDADevice_get_classification", "definition"),
    ("OpenFDADevice_search_510k", "decision_code"),
    ("OpenFDADevice_search_pma", "supplement_number"),
    ("MaveDB_get_score_set", "score_calibrations"),
    ("MaveDB_get_score_set", "score_distribution"),
    ("MaveDB_get_score_set", "dataset_columns"),
    ("MaveDB_get_score_set", "experiment"),
    ("MaveDB_get_clinical_controls", "variant_links"),
    ("MaveDB_search_experiments", "keywords"),
    ("MaveDB_search_experiments", "method"),
    ("MaveDB_search_score_sets", "target_gene_details"),
    ("WormBase_get_phenotypes", "subjects"),
    ("WormBase_get_phenotypes", "reference_details"),
    ("WormBase_get_phenotypes", "annotation_types"),
    ("WormBase_get_expression", "annotations"),
    ("WormBase_get_orthologs", "methods_not_called"),
    ("WormBase_get_interactions", "detection_method"),
    ("WormBase_get_interactions", "phenotypes_or_traits"),
    ("WormBase_get_human_diseases", "annotated_disease_count"),
    ("WormBase_get_human_diseases", "has_annotations"),
    ("USDA_plants_get_profile", "ancestors"),
    ("USDA_plants_get_profile", "map_coordinates"),
    ("USDA_plants_get_profile", "available_data"),
    ("USDA_plants_get_profile", "synonym_note"),
    ("USDA_plants_search_by_name", "accepted_symbol"),
    ("CancerPrognosis_search_studies", "sample_counts"),
    ("CancerPrognosis_search_studies", "reference_genome"),
    ("CancerPrognosis_search_studies", "cancer_type_name"),
    ("CancerPrognosis_get_study_summary", "datatype"),
    ("CancerPrognosis_get_gene_expression", "profile_datatype"),
    ("FDA_OrangeBook_get_approval_history", "products"),
    ("FDA_OrangeBook_get_approval_history", "identifiers"),
    ("FDA_OrangeBook_get_te_code", "dosage_form"),
    ("FDA_OrangeBook_search_drug", "identifiers"),
    ("NCBIDatasets_get_gene", "gene_ontology"),
    ("NCBIDatasets_get_gene", "summary"),
    ("NCBIDatasets_get_taxonomy", "genetic_code"),
    ("NCBIDatasets_get_orthologs", "gene_ontology_counts"),
    ("ClinGen_get_variant_classifications", "Warnings"),
    ("ClinGen_get_variant_classifications", "Guidelines"),
    ("EWASAtlas_search_by_gene", "transcripts"),
    ("EWASAtlas_get_study", "sd_age"),
    ("BioBankJapan_phewas_by_variant", "num_samples"),
    ("Genebass_gene_burden_phewas", "n_cases"),
    ("Genebass_gene_burden_phewas", "pval_skato"),
    ("ols_get_efo_term", "term_replaced_by"),
    ("ols_list_ontologies", "languages"),
    ("RGD_get_annotations", "object_symbol"),
    ("RGD_get_annotations", "reference_rgd_id"),
    ("RGD_get_qtls_in_region", "peak_rgd_id"),
    ("RGD_search_genes", "diseases"),
    ("RGD_get_orthologs", "refseq_status"),
    ("RGD_search_strains", "last_status"),
    ("IMPC_get_phenotypes_by_gene", "statistical_method"),
    ("IMPC_get_gene_summary", "allele_names"),
    ("IMPC_search_genes", "marker_type"),
    ("Progenetix_search_biosamples", "pathological_tnm_findings"),
    ("Progenetix_list_cohorts", "reference"),
    ("HMDB_get_diseases", "mesh_chemical_id"),
    ("HMDB_get_diseases", "ctd_terms_tried"),
    ("UniProt_search", "reviewed"),
    ("UniProt_search", "feature_types"),
    ("UniProt_search", "cross_reference_databases"),
    ("UniProtRef_get_proteome", "citations"),
    ("UniProtRef_get_proteome", "busco"),
    ("UniProtRef_search_keywords", "gene_ontologies"),
    ("QuickGO_annotations_by_goterm", "reference"),
    ("QuickGO_get_term_detail", "children"),
    ("ReactomeContent_search", "summation"),
    ("Pfam_get_protein_annotations", "protein_accession"),
    ("Pfam_get_family_proteins", "source_database"),
    ("FAERS_search_adverse_event_reports", "rxcui"),
    ("ClinGenAR_lookup_allele", "gene_symbol"),
    ("ClinGenAR_lookup_allele", "protein_effect"),
    ("ClinGenAR_lookup_allele", "mane_select_transcript"),
    ("ClinGenAR_lookup_allele", "transcript_alleles_truncated"),
    ("ClinGenAR_get_external_records", "record_count"),
    ("ClinGenAR_lookup_by_external_id", "transcript_alleles"),
    ("EPMC_get_text_mined_annotations", "tags"),
    ("EPMC_get_text_mined_annotations", "providers"),
    ("EPMC_get_article_genes", "mentions"),
    ("EPMC_get_article_genes", "returned_entities"),
    ("DrugCentral_get_drug", "pharmacologic_classes"),
    ("DrugCentral_get_drug", "adverse_event_signals_truncated"),
    ("DrugCentral_get_drug", "dosages"),
    ("DrugCentral_get_targets", "swissprot_entries"),
    ("DrugCentral_search", "cross_references"),
    ("Bgee_get_gene_expression", "fdr"),
    ("Bgee_search_genes", "matched_text"),
    ("Bgee_list_species", "parent_taxon_id"),
    ("MedlinePlus_get_genetics_condition_by_name", "cross_references"),
    ("MedlinePlus_get_genetics_gene_by_name", "gene_symbol"),
    ("MedlinePlus_connect_lookup_by_code", "resolved_query"),
    ("EBIProteins_get_domains_sites", "ligand"),
    ("EBIProteins_get_molecule_processing", "feature_id"),
    ("ChEBI_get_compound", "inchi"),
    ("ChEBI_get_compound", "roles"),
    ("ChEBI_get_compound", "cas_numbers"),
    ("ChEBI_get_compound", "synonym_details"),
    ("ChEBI_search", "smiles"),
    ("ChEBI_get_ontology_parents", "name"),
    ("ols_search_terms", "related_synonyms"),
    ("ols_get_ontology_info", "importsFrom"),
    ("ols_find_similar_terms", "source_term"),
    ("ITIS_get_full_record", "accepted_names"),
    ("ITIS_get_full_record", "synonyms_truncated"),
    ("ITIS_get_full_record", "jurisdictional_origins"),
    ("ITIS_get_hierarchy", "parent_name"),
    ("GBIF_get_taxon_children", "kingdomKey"),
    ("GBIF_get_taxon_children", "issues"),
    ("GBIF_get_vernacular_names", "preferred"),
    ("HuBMAP_list_organs", "laterality"),
    ("HuBMAP_list_organs", "category_term"),
    ("HuBMAP_get_dataset_provenance", "donor_attributes"),
    ("RxClass_get_class_members", "relation"),
    ("RxClass_find_classes", "classUrl"),
    ("RxClass_get_disease_relations", "relaSource"),
    ("EBIProteins_get_coordinate_mapping", "feature_type_counts"),
    ("EBIProteins_get_coordinate_mapping", "assembly_name"),
    ("EBIProteins_get_proteins_by_genomic_loc", "features_truncated"),
    ("EBIProteins_get_interaction_details", "disease_records"),
    ("EBIProteins_get_interaction_details", "subcellular_location_records"),
    ("EBIProteins_get_interaction_details", "intact_id_a"),
    ("SwissModel_get_models", "ligands"),
    ("SwissModel_get_models", "oligo_state"),
    ("SwissModel_get_summary", "models_with_ligands"),
    ("HuBMAP_get_sample", "descendant_count"),
    ("HuBMAP_get_sample", "donor_demographics"),
    ("OSDR_get_study", "protocol_descriptions"),
    ("OSDR_get_study", "investigator"),
    ("OSDR_search_studies", "data_source_type"),
    ("OSDR_list_files", "organization"),
    ("UniProtIDMap_list_databases", "to_supported"),
    ("UniProtIDMap_list_databases", "uri_template"),
    ("UniProtIDMap_gene_to_uniprot", "reviewed"),
    ("GWASSumStats_get_trait_studies", "summary_statistics"),
    ("GWASSumStats_get_trait_studies", "initial_sample_description"),
    ("GWASSumStats_list_studies", "discovery_sample_ancestry"),
    ("ClinicalTrials_get_study", "secondary_outcomes"),
    ("ClinicalTrials_get_study", "other_outcome_count"),
    ("ClinicalTrials_search_studies", "primary_outcome_measures"),
    ("ClinicalTrials_search_studies", "arm_count"),
    ("FoodDataCentral_search_foods", "derivation_description"),
    ("CxGDisc_list_collections", "publication"),
    ("CxGDisc_list_collections", "tissue_count"),
    ("CxGDisc_list_collections", "datasets_with_cell_count"),
    ("NCIEVS_search_terminology", "concept_status"),
    ("Nextstrain_get_dataset", "colorings"),
    ("ORCID_get_peer_reviews", "subgroup_external_ids"),
    ("ORCID_get_peer_reviews", "visibility"),
    ("FDA_OrangeBook_check_generic_availability", "original_approval_date"),
    ("FDA_OrangeBook_search_drug", "submission_count"),
    ("ExpressionAtlas_get_baseline", "experimental_factors"),
    ("ExpressionAtlas_get_baseline", "technology_type"),
    ("HuBMAP_get_sample", "donor_demographics_coded"),
    ("HuBMAP_search_donors", "demographics_coded"),
    ("DDBJ_get_entry", "cross_reference_types"),
    ("TIMER2_immune_estimation", "study_sample_total"),
    ("TIMER2_immune_estimation", "sampling"),
    ("TIMER2_immune_estimation", "n_paired_samples"),
    ("OpenGenes_get_gene", "evidence_summary"),
    ("OpenGenes_get_gene", "aging_mechanisms"),
    ("CATH_get_domain_summary", "go_terms"),
    ("CATH_get_domain_summary", "pdb_segments"),
    ("Orphanet_get_genes", "Synonyms"),
    ("Orphanet_get_genes", "ExternalReferences"),
    ("UniProtRef_search_proteomes", "taxon_lineage_nodes"),
    ("UniProtRef_search_proteomes", "component_names"),
    ("ClinicalTrials_get_study", "has_results"),
    ("ClinicalTrials_get_study", "results_summary"),
    ("UCSCCellBrowser_search_datasets", "sample_count"),
    ("UCSCCellBrowser_search_datasets", "has_files"),
    ("SCREEN_search_cCREs_by_region", "length"),
    ("SGD_get_gene", "phenotype_summary"),
    ("SGD_get_gene", "allele_records"),
    ("SGD_get_gene", "slim_set"),
    ("GenomeNexus_get_cancer_hotspots", "variant_summary"),
    ("GenomeNexus_get_cancer_hotspots", "colocated_variant_ids"),
    ("Ensembl_get_species_info", "groups"),
    ("miRBase_get_mirna_publications", "pub_id"),
    ("DANDI_search_datasets", "version_is_published"),
    ("DANDI_search_datasets", "draft_asset_count"),
    ("MAGICapp_list_guidelines", "institutionName"),
    ("MAGICapp_list_guidelines", "publishLastSearchDate"),
    ("MAGICapp_list_guidelines", "isLatestPublished"),
    ("PubChemBioAssay_search_by_gene", "compound_counts"),
    ("PubChemBioAssay_search_by_gene", "source_id"),
    ("PubChemBioAssay_get_assay_summary", "protocol"),
    ("PubChemBioAssay_get_assay_summary", "comment"),
    ("GOAPI_get_gene_functions", "evidence_codes"),
    ("GOAPI_get_gene_functions", "negated"),
    ("GOAPI_get_genes_by_function", "negated_associations"),
    ("InterPro_get_entries_for_protein", "match_locations"),
    ("InterPro_get_entries_for_protein", "go_terms"),
    ("Harmonizome_search_genes", "synonyms"),
    ("Harmonizome_search", "synonyms"),
    ("dbsnp_get_frequencies", "studies_unparsed"),
    ("dbsnp_get_frequencies", "all_studies_parsed"),
    ("FlyBase_get_gene_orthologs", "is_paralogy"),
    ("ZFIN_get_gene_orthologs", "relationship"),
    ("Alliance_get_gene_orthologs", "similarity_percent"),
    ("gather_drug_profile", "synonym_details"),
    ("gather_drug_profile", "synonym_type_counts"),
    ("OPM_search_structures", "transmembrane_segments"),
    ("OPM_search_structures", "comments"),
    ("OPM_search_structures", "uniprot_entry_names"),
    ("MCSA_get_entry", "auth_residue_number"),
    ("MCSA_get_entry", "role_details"),
    ("MCSA_get_entry", "function_type"),
    ("MCSA_get_entry", "reaction_compounds"),
    ("MCSA_get_entry", "mechanisms"),
    ("MCSA_search_enzymes", "auth_residue_number"),
    ("MCSA_search_enzymes", "mechanism_count"),
    ("hca_search_projects", "genusSpecies"),
    ("hca_search_projects", "libraryConstructionApproach"),
    ("hca_search_projects", "totalCells"),
    ("hca_search_projects", "projectTitle"),
    ("hca_get_file_manifest", "sha256"),
    ("hca_get_file_manifest", "is_intermediate"),
    ("NDEx_get_network", "attributes"),
    ("NDEx_get_network", "edge_attribute_names"),
    ("NDEx_get_network", "network_attributes"),
    ("InterPro_get_proteins_by_domain", "match_locations"),
    ("InterPro_get_proteins_by_domain", "entry_type"),
    ("InterPro_get_proteins_by_domain", "in_alphafold"),
    ("Mondo_search_disease", "score"),
    ("Mondo_search_disease", "match_type"),
    ("Mondo_search_disease", "synonyms"),
    ("PDBe_KB_get_ligand_sites", "start_code"),
    ("PDBe_KB_get_ligand_sites", "index_type"),
    ("PDBe_KB_get_ligand_sites", "interacting_pdb_entries"),
    ("PDBe_KB_get_ligand_sites", "scaffold_smiles"),
    ("PDBe_KB_get_interface_residues", "start_code"),
    ("DepMap_get_cell_lines", "data_available"),
    ("DepMap_get_cell_lines", "mutations_per_mb"),
    ("iNaturalist_get_taxon", "conservation_status_detail"),
    ("iNaturalist_get_taxon", "place_listings"),
    ("iNaturalist_get_taxon", "place_listings_total"),
    ("iNaturalist_search_taxa", "conservation_status_detail"),
    ("ThreeDBeacons_get_structures", "model_format"),
    ("ThreeDBeacons_get_structures", "entities"),
    ("ThreeDBeacons_get_structures", "entity_counts_by_type"),
    ("ThreeDBeacons_get_structures", "sequence_identity"),
    ("FinnGen_list_phenotypes", "gc_lambda"),
    ("FinnGen_list_phenotypes", "assoc_files"),
    ("FinnGen_get_phenotype", "assoc_files"),
    ("FDAGSRS_get_substance", "citations"),
    ("FDAGSRS_get_substance", "comments"),
    ("FDAGSRS_get_substance", "jurisdictions"),
    ("FDAGSRS_get_substance", "references"),
    ("MGI_get_phenotypes", "phenotype_terms"),
    ("MGI_get_phenotypes", "data_providers"),
    ("MGI_get_phenotypes", "annotation_subjects"),
    ("ZFIN_get_gene_phenotypes", "phenotype_terms"),
    ("ZFIN_get_gene_phenotypes", "annotation_relations"),
    ("NIHDSLD_get_label", "statements"),
    ("NIHDSLD_get_label", "other_ingredients"),
    ("NIHDSLD_get_label", "percent_dv_footnote"),
    ("NIHDSLD_get_label", "net_contents"),
    ("PGSCatalog_search_traits", "associated_pgs_ids"),
    ("PGSCatalog_search_traits", "child_associated_pgs_ids"),
    ("PGSCatalog_search_traits", "trait_synonyms"),
    ("Alliance_get_disease_genes", "evidence_code_details"),
    ("Alliance_get_disease_genes", "annotation_relations"),
    ("NCIThesaurus_get_concept", "is_preferred_name"),
    ("NCIThesaurus_get_concept", "annotation_property"),
    ("IGSR_search_populations", "data_collections"),
    ("IGSR_search_populations", "data_reuse_policy"),
    ("IGSR_search_populations", "data_collection_details"),
    ("IGSR_search_samples", "data_collection_details"),
    ("InterPro_get_structures_for_domain", "structure_locations"),
    ("InterPro_get_structures_for_domain", "auth_start"),
    ("InterPro_get_structures_for_domain", "chains"),
    ("NDEx_search_networks", "cx2_file_size"),
    ("GeneBe_classify_variant", "clinvar_review_status"),
    ("GeneBe_classify_variant", "clinvar_submissions_summary"),
    ("GeneBe_classify_variant", "mane_select"),
    ("GeneBe_classify_variant", "consequence_count"),
    ("InterPro_get_protein_domain_architecture", "protein_source_database"),
    ("OSDR_search_studies", "assay_technology_platform"),
    ("OSDR_search_studies", "project_type"),
    ("cBioPortal_get_copy_number_alterations", "molecular_profile"),
    ("cBioPortal_get_copy_number_alterations", "molecular_profile_resolution"),
    ("SmartAPI_search_apis", "base_url_maturity"),
    ("SmartAPI_search_apis", "servers"),
    ("SmartAPI_search_apis", "maturity"),
    ("NCIThesaurus_get_concept", "definition_source"),
    ("NCIThesaurus_get_concept", "definition_count"),
    ("GeneBe_classify_variant", "acmg_gene_count"),
    ("ZFIN_get_gene_expression", "uberon_term_ids"),
    ("ZFIN_get_gene_expression", "anatomical_structure_curie"),
    ("ZFIN_get_gene_expression", "assay_curie"),
    ("proteins_api_get_proteomics", "proteomics_cross_references"),
    ("proteins_api_get_proteomics", "proteomics_databases"),
    ("UniProtTaxonomy_search", "other_names"),
    ("UniProtTaxonomy_search", "parent_taxon_id"),
    ("Ensembl_get_assembly_info", "other_regions"),
    ("Ensembl_get_assembly_info", "coord_system"),
    ("DbGaP_get_study", "condition_codes"),
    ("DbGaP_get_study", "keyword_codes"),
    ("DbGaP_search_studies", "condition_codes"),
    ("ClinVar_search_by_region", "gene_count"),
    ("ClinVar_search_by_region", "accession"),
    ("ClinVar_search_by_region", "review_status"),
]


# JSON-Schema's own annotation keys. A DECLARED row naming one of these can
# never fail -- `"description"` appears in every schema that documents
# anything -- so the row would look like a guard and be a no-op. OSDR's
# `description` was exactly that for one commit; assert such a row instead in
# a named test, against the text of its own declaration.
SCHEMA_KEYWORDS = frozenset(
    {
        "description", "type", "properties", "items", "required", "enum",
        "oneOf", "anyOf", "allOf", "not", "default", "format", "title",
        "additionalProperties", "minimum", "maximum", "pattern",
    }
)


def test_no_declared_row_names_a_json_schema_keyword():
    """A guard that cannot fail is worse than no guard: it reads as coverage."""
    vacuous = sorted({f for _, f in DECLARED if f in SCHEMA_KEYWORDS})
    assert not vacuous, (
        f"DECLARED rows for {vacuous} would pass against any schema that "
        "documents anything; assert them in a named test instead"
    )


@pytest.mark.parametrize("tool, field", DECLARED, ids=[f"{t}:{f}" for t, f in DECLARED])
def test_the_return_schema_declares_the_field_the_wrapper_now_returns(tool, field):
    """A field the caller cannot find in the schema is barely less hidden.

    The wrapper carrying it and the schema not declaring it is the shape that
    let these drops survive: an agent reads the schema to decide what a tool
    can answer.
    """
    schema = json.dumps(_config(tool).get("return_schema") or {})
    assert f'"{field}"' in schema, (
        f"{tool} returns `{field}` and its return_schema does not declare it"
    )


def test_a_uniprot_search_hit_says_whether_it_is_reviewed():
    """Swiss-Prot or TrEMBL is the biggest quality distinction in UniProt.

    `entryType` is "UniProtKB reviewed (Swiss-Prot)" or "UniProtKB unreviewed
    (TrEMBL)" on every entry of every search, and the row carried six fields
    that did not include it -- so a curated human entry and an unreviewed
    machine annotation came back looking identical. The annotation score and
    the protein-existence evidence level, the other two quality signals on
    the same entry, went with it.
    """
    source = _source("uniprot_tool.py")
    assert 'entry.get("entryType")' in source
    assert '"reviewed"' in source
    assert 'entry.get("annotationScore")' in source


def test_an_impc_phenotype_hit_says_how_it_was_called():
    """A phenotype hit is a statistical result.

    Which pipeline ran it, which test produced the p-value and which IMPC
    data release it comes from were all in the Solr `fields` the tool itself
    asked for, and the row dropped them -- so "preweaning lethality,
    incomplete penetrance, p=1e-6" arrived with no way to tell a
    Supplied-as-data call from a Fisher exact one.
    """
    source = _source("impc_tool.py")
    assert source.count('doc.get("statistical_method")') >= 2
    assert 'doc.get("pipeline_name")' in source
    assert 'doc.get("resource_name")' in source


def test_an_obsolete_efo_term_says_what_replaced_it():
    """EFO:0000400 is "obsolete_diabetes mellitus" and MONDO_0005015 replaced it.

    The tool reported `is_obsolete: true` and stopped there, from a record
    that names the replacement in `annotation.term_replaced_by` -- so a caller
    looking up diabetes got a dead term and no pointer to the live one.
    """
    source = _source("efo_tool.py")
    assert 'annotation.get("term_replaced_by")' in source
    assert 'annotation.get("has_alternative_id")' in source


def test_a_burden_p_value_comes_with_its_sample_size():
    """4,529 Genebass associations, and not one of them said n.

    The case and control counts are on the phenotype catalogue the tool
    already fetches to get each phenotype's description, and only the
    description was kept. A burden p-value with no n cannot be read.
    """
    source = _source("pheweb_phewas_tool.py")
    assert 'p.get("n_cases")' in source
    assert 'record.get("description")' in source, (
        "the catalogue join is what carries them"
    )
    # And a quantitative trait's n, which is not a case count at all.
    assert 'p.get("num_samples")' in source


def test_a_te_code_names_the_product_it_applies_to():
    """"AB" for the 80 mg tablet says nothing about the oral solution.

    Therapeutic equivalence is a property of a product -- a dosage form, a
    route and a strength -- and the row carried the brand name, the code and
    the application number, leaving the caller to assume one TE code covered
    every form the brand is sold in.
    """
    source = _source("fda_orange_book_tool.py")
    assert '"dosage_form": product.get("dosage_form")' in source
    assert '"active_ingredients": product.get(' in source


def test_cbioportal_sample_counts_are_not_one_number():
    """`max()` of three counts, and no way to tell which one it was.

    BRCA TCGA has 1,108 samples, 982 sequenced, 1,080 with CNA, 1,100 with
    RNA-seq v2, 529 with microarray, 316 with HM27 methylation and 892 with
    RPPA. A study that can answer an expression question may not be able to
    answer a methylation one, and `sample_count` could not tell them apart.
    """
    source = _source("cancer_prognosis_tool.py")
    assert "_study_counts" in source
    assert "methylationHm27SampleCount" in source
    assert "rppaSampleCount" in source


def test_usda_says_when_a_symbol_was_a_synonym():
    """USDA redirects a synonym to the accepted taxon in silence.

    `symbol=AGRE2` answers the profile of ELRE4, Elymus repens -- and the
    symbol asked for and the symbol answered sat in two different parts of
    the response, data and metadata, with nothing stating the substitution.
    Four sibling tools paid for the same profile only to turn a symbol into a
    numeric id and then threw it away, so a wetland or invasive answer named
    neither the species nor the swap.
    """
    source = _source("usda_plants_tool.py")
    assert "def _plant_identity" in source
    assert "is a synonym; USDA PLANTS answered" in source
    # The resolver hands back the profile it already paid for.
    assert "return profile.get(\"Id\"), symbol, None, profile" in source


def test_wormbase_phenotypes_name_the_allele_they_belong_to():
    """A phenotype annotation's subject is the allele, not the gene.

    unc-26's "aldicarb resistant" is the phenotype of allele m2
    (WB:WBVar00088530); `inferredGene` is how it maps back to the gene. The
    tool reported the statement against the gene with no allele named, so two
    alleles with different phenotypes arrived as one undifferentiated list.
    """
    source = _source("wormbase_tool.py")
    assert 'subject_of.get("alleleSymbol")' in source or (
        '_text(subject_of.get("alleleSymbol"))' in source
    )
    assert 'a.get("inferredGene")' in source


def test_wormbase_disease_ribbon_counts_this_genes_annotations():
    """`disease_count` is the same for every gene: it counts ribbon categories.

    The ribbon answers two things and only one was read. `categories` is the
    Disease Ontology skeleton, every top-level category whether or not the
    gene has an annotation in it, and `subjects` carries this gene's counts
    per group. unc-26 has two disease annotations and was reported with five
    "diseases", none of them marked as the ones it actually has.
    """
    source = _source("wormbase_tool.py")
    assert "nb_annotations" in source
    assert '"has_annotations"' in source
    assert '"annotated_disease_count"' in source


def test_mavedb_clinical_controls_link_to_the_score_sets_own_variants():
    """The endpoint exists to connect a ClinVar call to a measured score.

    A clinical control answers "ClinVar calls 65709 in BRCA2 Pathogenic, by
    expert panel". The link to the score set's own variant arrives under
    `clinvarLinks` and was read from `mappedVariants`, which the response does
    not carry -- so `mapped_variant_urns` was empty on all 2,122 controls of
    urn:mavedb:00001263-a-2 and the one thing the caller came for was absent.
    """
    source = _source("mavedb_tool.py")
    assert 'entry.get("clinvarLinks")' in source
    assert 'entry.get("mappedVariants")' in source, (
        "keep the old spelling as a fallback rather than swapping one guess "
        "for another"
    )


def test_pubchem_tox_statements_say_who_stated_them():
    """An LD50 with no source is a number a reader cannot weigh.

    Every PUG View statement carries a `ReferenceNumber` and the record
    carries the references it points into -- ECHA for aspirin's GHS
    classification, IARC with its own copyright note for arsenic's carcinogen
    listing, ILO-WHO's ICSC for the acute signs. None of it reached the
    caller, and the licence terms travel with the source.
    """
    source = _source("pubchem_tox_tool.py")
    assert "_reference_index" in source
    assert '"license_note": reference.get("license_note")' in source or (
        'reference.get("license_note")' in source
    )
    # And the cut that used to happen in silence now says so.
    assert 'item["value"][:500]' not in source, (
        "a clinical description cut at 500 characters with no flag was the bug"
    )
    assert "effect_truncated" in source


def test_glygen_search_counts_the_sites_the_row_actually_reports():
    """Every result of every glycoprotein search said 0.

    `total_n_glycosites` and `total_o_glycosites` are not keys a
    /protein/list row carries; `reported_n_glycosites` and
    `reported_o_glycosites` are. With `or 0` wrapped around each missing key
    the sum came out as 0 on every row -- from a tool whose description
    promises "glycosylation-site counts" -- and HGF, which has four N-linked
    and one O-linked reported site, was indistinguishable from a protein with
    none. A count the API never sent now reads as null.
    """
    source = _source("glygen_tool.py")
    assert "reported_n_glycosites" in source
    assert "reported_o_glycosites" in source
    assert '(item.get("total_n_glycosites") or 0)' not in source, (
        "the sum of two absent keys was the bug, not the fix"
    )
    assert "_first_number" in source, (
        "a count must come back null when the row does not carry it"
    )


def test_gprofiler_says_when_it_could_not_resolve_a_gene():
    """Four genes in, one a typo, three tested, and nothing said.

    This is the paper's class in one call: the tool reported `query_size: 3`
    beside a p_value computed on three genes while the caller had submitted
    four, and `failed: ["NOTAGENE123"]` sat in the response it threw away.
    """
    source = _source("gprofiler_tool.py")
    assert "gene_resolution_warning" in source
    assert '"genes_failed"' in source
    assert '"genes_submitted"' in source
    config = _config("gProfiler_enrichment")
    assert "genes_failed" in config["description"], (
        "the disclosure is only useful if the description says it exists"
    )


def test_geo_no_longer_claims_the_sample_list_is_excluded_upstream():
    """The claim was about the esearch entry-type filter, not the sample list.

    `gse[ETYP]` does restrict the SEARCH to series. The esummary then answers
    every GSM of each series -- 82 for GSE313540 -- and the description's
    "GSM samples ... are excluded upstream" read as though that data did not
    exist.
    """
    text = (DATA / "epigenomics_tools.json").read_text()
    assert "excluded upstream" not in text, (
        "a description that says the samples are excluded upstream, beside a "
        "tool that now returns them, is worse than either alone"
    )
    assert "samples_truncated" in text


def test_doaj_keeps_the_article_keywords_apart_from_the_journal_subject():
    """The output field `keywords` used to hold `bibjson.subject`.

    Not a drop but a substitution: the LCC class "Chemical engineering" was
    returned under the name `keywords` while the article's own terms -- "oil
    palm shell", "pyrolysis" -- were never read. Both are reported now, each
    under its own name, so the next reader of this code does not re-merge them.
    """
    source = _source("doaj_tool.py")
    assert 'b.get("keywords")' in source, "the article's own keywords must be read"
    assert '"subjects": subjects' in source, (
        "the LCC classification must be reported as subjects, not as keywords"
    )


def test_expression_atlas_caveat_matches_what_the_response_holds():
    """The caveat named fields that are empty AND design data that is not.

    `experiment.experimentalFactors`, `technologyType`, `contrasts`,
    `numberOfAssays` and `pubmedIds` really are null -- measured live on
    E-MTAB-2836 -- so that half stays. The design is not missing: it is in
    `columnHeaders`, which the tool now reads.
    """
    config = _config("ExpressionAtlas_get_experiment")
    description = config["description"]
    assert "does not expose per-experiment design" not in description
    assert "assay_groups" in description
    assert "GxA_get_experiment_expression" in description, (
        "the tool that does return expression values should be named here"
    )


def test_the_clinical_trials_extractor_no_longer_deletes_its_evidence():
    """It did not omit these fields, it deleted them.

    `sourceVocabulary` names the MedDRA version a term comes from, and
    `assessmentType` separates a SYSTEMATIC_ASSESSMENT -- every participant
    checked for this event -- from a NON_SYSTEMATIC one, where a lower count
    may mean only that nobody looked. Comparing two arms across that
    difference is not valid. `numEvents` was deleted once a percentage had
    been computed from it, leaving a derived number with its input removed,
    and events are not participants: 5 events in 3 patients and 5 affected
    patients both arrived as "5".
    """
    source = _source("ctg_tool.py")
    assert 'del ae["sourceVocabulary"]' not in source
    assert 'del ae["assessmentType"]' not in source
    assert 'del group_stats["numEvents"]' not in source


def test_sgd_reads_the_interaction_direction_instead_of_assuming_it():
    """46% of rows were reported with bait and hit the wrong way round.

    SGD states the direction in `bait_hit`. On S000003219's 180 interactions,
    83 are "Hit-Bait", meaning locus1 is the hit -- and locus1 was labelled
    the bait unconditionally, which for a two-hybrid result inverts which
    protein was the probe.
    """
    source = _source("sgd_tool.py")
    assert 'bait_hit.strip().lower().startswith("hit")' in source, (
        "the direction must be read from bait_hit, not assumed from position"
    )
    assert "bait, hit = locus2, locus1" in source


def test_the_monarch_schemas_say_what_the_rows_hold():
    """Six of seven declared `{"type": "array"}` and nothing else.

    A schema that declares no properties is not a smaller problem than a
    dropped field; it is the reason a dropped field is invisible. Nothing
    static could show that `MonarchV3_get_associations` returned 9 of the 37
    fields Biolink puts on an association.
    """
    for tool in [
        "MonarchV3_get_entity",
        "MonarchV3_get_associations",
        "MonarchV3_search",
        "MonarchV3_get_mappings",
        "MonarchV3_phenotype_similarity_search",
    ]:
        schema = json.dumps(_config(tool).get("return_schema") or {})
        assert schema not in ('{"type": "array"}', '{"type": "object"}', "{}"), (
            f"{tool} still declares nothing about its rows"
        )
        assert '"properties"' in schema, f"{tool} declares no properties"


def test_sgd_says_which_strain_a_sequence_came_from():
    """ "Take S288C, falling back to the first" across 41 strains, silently.

    A caller comparing the returned coordinates to the reference genome could
    have been comparing against another isolate, with nothing in the response
    to say so.
    """
    source = _source("sgd_tool.py")
    assert '"strains_available"' in source
    assert '"is_reference_strain"' in source


def test_a_clingen_allele_names_its_gene_and_protein_change():
    """The tool's own description promises 'CA000387 (TP53 p.Arg248Gln)'.

    Both of those live only on `transcriptAlleles`, which the wrapper never
    read: it returned the CA id, the community standard title and the first
    genomic HGVS. CA000387 has 65 transcript alleles and the MANE Select one
    is the representation the registry exists to normalise to, so it is
    surfaced whatever its position in the list, the rest are capped, and the
    cap is disclosed.
    """
    source = _source("clingen_ar_tool.py")
    assert "TRANSCRIPTS_PER_ALLELE" in source
    assert '"mane_select_transcript": mane' in source
    assert '"transcript_alleles_truncated": len(rows) > TRANSCRIPTS_PER_ALLELE' in source
    schema = json.dumps(_config("ClinGenAR_lookup_allele").get("return_schema") or {})
    assert '"mane_refseq_hgvs"' in schema


def test_a_clingen_external_record_has_an_id_under_the_name_it_uses():
    """`rec.get("id")` returned None for the databases that matter most.

    dbSNP sends `rs`, ClinVar alleles send `alleleId` and ClinVar variations
    send `variationId`; none of them sends `id`. So a tool whose description
    promises "dbSNP rsIDs" answered `{"id": null, "url": ".../snp/113488022"}`
    -- the rsID only inside a URL -- and dropped the ClinVar preferred name,
    the 30 RCV accessions and the gnomAD variant string with it.
    """
    source = _source("clingen_ar_tool.py")
    assert '_ID_KEYS = ("rs", "alleleId", "variationId"' in source
    assert 'f"rs{rec[key]}" if key == "rs" else str(rec[key])' in source


def test_an_epmc_relationship_annotation_keeps_both_ends():
    """A Gene Disease Relationship has two tags, and tags[0] is one of them.

    Open Targets contributes relationship annotations to Europe PMC whose
    `tags` carry the gene and the disease together: on PMID 33332779 one of
    them is interleukin-6 receptor *and* pneumonia *and* Covid-19. The
    wrapper read `tags[0]`, so the relationship arrived as its subject with
    the object silently gone -- and 17 of that article's 347 annotations are
    of that shape.
    """
    source = _source("epmc_annotations_tool.py")
    assert "def _tags(" in source
    assert '"tags": tags' in source
    assert '"tag_count"' in source
    schema = json.dumps(
        _config("EPMC_get_text_mined_annotations").get("return_schema") or {}
    )
    assert '"mentions_truncated"' in schema


def test_a_drugcentral_signal_comes_with_the_threshold_it_is_measured_against():
    """An llr of 44808 means nothing without llr_threshold of 9.445.

    DrugCentral ships a FAERS disproportionality row per MedDRA term -- 1,534
    for metformin, the strongest of them lactic acidosis -- and the whole
    section was dropped from a tool whose description promises "comprehensive
    drug data". Rows are ranked by llr, capped, and the cut is disclosed; the
    pair is reported together with is_signal, and the metadata says a signal
    is a reporting association and not causation.
    """
    source = _source("drugcentral_tool.py")
    assert "SIGNALS_PER_DRUG" in source
    assert '"is_signal"' in source
    assert "not evidence of causation" in source
    assert '"adverse_event_signals_truncated"' in source


def test_a_bgee_expression_call_reports_its_fdr():
    """`quality: "gold"` is the summary of the FDR, not the FDR.

    All 145 calls for TP53 carry `fdr` and all 145 lost it, while the
    qualitative grade derived from it was kept. The gene the response was
    answered for was dropped too, so a wrong gene id and a gene with no calls
    were the same empty answer.
    """
    source = _source("bgee_tool.py")
    assert 'call.get("fdr")' in source
    assert '"cluster_index": call.get("clusterIndex")' in source
    assert '"gene": {' in source


def test_an_itis_invalid_name_says_what_replaced_it():
    """"invalid" without the accepted name is half an answer.

    TSN 944513 is reported `usage_rating: "invalid"`, and the same response
    says it is a "junior synonym" of Homo sapiens, TSN 180092 -- both in
    `acceptedNameList` and `unacceptReason`, neither of which was read. The
    record also held 29 synonyms, 7 jurisdictional origins (Native in Alaska,
    and so on), the Taxonomic Work Group's credibility verdict, and the
    publications and experts the tool's own docstring promises as "authority
    references".
    """
    source = _source("itis_tool.py")
    assert '_rows(data.get("acceptedNameList"), "acceptedNames")' in source
    assert '"unaccept_reason"' in source
    assert '"synonyms_truncated"' in source
    assert "SYNONYMS_PER_RECORD" in source
    schema = json.dumps(_config("ITIS_get_full_record").get("return_schema") or {})
    assert '"unaccept_reason"' in schema


def test_a_hubmap_contributor_orcid_is_not_null():
    """`person.get("orcid")` against an API that sends `orcid_id`.

    Every contributor on HBM626.FHJD.938 has an ORCID and every one of them
    came back null -- the shape where a key the API does not send is read and
    the absence looks like missing data upstream.
    """
    source = _source("hubmap_tool.py")
    assert 'person.get("orcid") or person.get("orcid_id")' in source


def test_a_hubmap_provenance_chain_says_what_the_donor_was():
    """The chain ends at a Donor whose attributes were not reported.

    The lineage row carried seven keys, none of them the donor's age, sex or
    race -- which `metadata.organ_donor_data` holds in the same response, as
    UMLS-coded assertions. Walking Dataset -> Sample -> Donor and then not
    saying who the donor was is most of the question left unanswered.
    """
    source = _source("hubmap_tool.py")
    assert "def _donor_attributes" in source
    assert "organ_donor_data" in source
    assert '"spatial_annotations": _ccf_annotations(entity)' in source


def test_an_rxclass_member_says_whether_it_is_a_direct_member():
    """DIRECT and INDIRECT membership are different claims.

    RxClass states it per member in `nodeAttr`, along with the source's own id
    for the member -- M01AE07 for suprofen under ATC M01AE -- and the row
    reported rxcui, name and tty, so a member of a descendant class was
    indistinguishable from a member of the class asked about.
    """
    source = _source("rxclass_tool.py")
    assert 'by_name.get("Relation")' in source
    assert 'by_name.get("SourceId")' in source


def test_a_chebi_compound_reports_its_cas_number_and_its_roles():
    """Aspirin's 50-78-2 was in the response and was not returned.

    `database_accessions` holds four sections -- CAS, registry numbers, 68
    PubMed citations and the manual cross-references -- and none was read.
    Nor was `roles_classification`, which is 36 entries for aspirin and is the
    half of ChEBI that is an ontology rather than a structure database. The
    synonym list also flattened a ChEMBL BRAND NAME and an IUPAC NAME into one
    undifferentiated list of strings.
    """
    source = _source("chebi_tool.py")
    assert "def _accessions" in source
    assert "def _roles" in source
    assert '"synonym_details": synonym_detail_page' in source
    schema = json.dumps(_config("ChEBI_get_compound").get("return_schema") or {})
    assert '"cas_numbers_total"' in schema


def test_an_ols_search_hit_carries_the_definition_it_arrived_with():
    """A term search answering a label and an id costs a call per hit.

    Every /api/search doc carries `description`, `exact_synonyms`,
    `related_synonyms`, `type` and `ontology_prefix`, and the row model had
    six fields that included none of them. The definition is also where OLS
    records a merge: ZFA:0009046's says CL:0000804 and CL:0000812 were merged
    into CL:0000084.
    """
    source = _source("ols_tool.py")
    assert 'item.get("exact_synonyms")' in source
    assert "def _as_string_list" in source
    schema = json.dumps(_config("ols_search_terms").get("return_schema") or {})
    assert '"related_synonyms"' in schema
    assert '"items"' in schema, "the terms array declared nothing about its rows"


def test_a_gbif_tree_walker_returns_the_keys_to_walk_with():
    """Seven rank names, no rank keys, on a tool for navigating a tree.

    `_slim_usage` projected onto 19 of the 38 fields a name-usage record
    carries: the kingdom/phylum/class/order/family/genus/species names were
    in and the matching `...Key` values were out, so following the lineage
    needed a name search per step. `issues` -- GBIF's own quality flags, e.g.
    NAME_PARENT_MISMATCH -- and the dataset the record came from were dropped
    too.
    """
    source = _source("gbif_taxonomy_tool.py")
    for key in ("kingdomKey", "phylumKey", "classKey", "orderKey", "familyKey",
                "genusKey", "speciesKey", "issues", "datasetKey"):
        assert f'"{key}"' in source, f"_slim_usage still drops {key}"


def test_a_binding_site_names_what_binds_there():
    """EGFR 718-726 binds ATP, CHEBI:30616, and said only 718-726.

    Four of P00533's eleven DOMAINS_AND_SITES features carry a `ligand`, and
    the category's own description is "binding sites, DNA binding regions,
    motifs, regions". The MOLECULE_PROCESSING features lost `ftId` the same
    way -- PRO_0000015819 is the insulin B chain, and it is how a processed
    chain is cited.
    """
    source = _source("ebi_proteins_features_tool.py")
    assert 'f.get("ligand")' in source
    assert 'f.get("ftId")' in source
    schema = json.dumps(
        _config("EBIProteins_get_domains_sites").get("return_schema") or {}
    )
    assert '"ligand"' in schema


def test_an_intronic_clingen_coordinate_keeps_its_offset():
    """`start: 1258` is not where the variant is when the offset is 3918.

    For an intronic variant the registry gives the position as an exon
    boundary plus an offset into the intron and a direction: 12 of the
    transcript alleles on the page for rs113488022 read start 1258 with
    startIntronOffset 3918 in the '-' direction, i.e. 1258-3918. Reporting
    1258 alone is not a field omitted, it is a different position asserted --
    an exonic one.
    """
    source = _source("clingen_ar_tool.py")
    assert 'coord.get("startIntronOffset")' in source
    assert 'coord.get("startIntronDirection")' in source
    assert '"is_intronic"' in source
    schema = json.dumps(_config("ClinGenAR_lookup_allele").get("return_schema") or {})
    assert '"start_intron_offset"' in schema


def test_both_ebi_interaction_tools_return_the_intact_ids():
    """One handler returned them and its sibling over the same endpoint did not.

    `interactor1` and `interactor2` are the IntAct interactor ids, without
    which a row cannot be followed into IntAct. A substring anchor is no use
    here -- the name was already in the file once, in the handler that did
    read it -- so this counts both reads.
    """
    source = _source("ebi_proteins_interactions_tool.py")
    assert source.count('interaction.get("interactor1")') == 2, (
        "get_interactions reads the IntAct ids and get_interaction_details "
        "must read them too"
    )
    assert source.count('interaction.get("interactor2")') == 2



def test_a_coordinate_mapping_returns_the_annotations_it_mapped():
    """16,654 features came back for TP53 and none reached the caller.

    `/coordinates/{acc}` attaches UniProt's whole feature table to each
    transcript mapping, already projected onto the genome -- 1,514 on TP53's
    first transcript, 1,363 of them sequence variants with their VAR ids and
    their genome positions. The tool paged the exons carefully and never
    looked at the features. It also dropped `assemblyName`, so the genome
    positions it did return came without the assembly they are against.
    """
    source = _source("ebi_proteins_coordinates_tool.py")
    assert "FEATURES_PER_MAPPING" in source
    assert "def _feature_page" in source
    assert 'genomic_loc.get("assemblyName")' in source
    schema = json.dumps(
        _config("EBIProteins_get_coordinate_mapping").get("return_schema") or {}
    )
    assert '"feature_type_counts"' in schema


def test_an_ebi_disease_annotation_keeps_its_omim_id_and_its_text():
    """`diseaseId or acronym` and discard the rest dropped three things.

    The OMIM id is in `dbReference`, the definition in `description`, and one
    of TP53's nine disease records has no diseaseId at all -- it is the
    free-text disease involvement paragraph, so the name list dropped it
    entirely rather than listing it without a name.
    """
    source = _source("ebi_proteins_interactions_tool.py")
    assert "def _disease_rows" in source
    assert 'row.get("dbReference")' in source
    assert "def _location_rows" in source
    # The name lists stay, so a caller reading `diseases` still works.
    assert '"diseases": sorted(diseases)' in source


def test_a_swiss_model_structure_names_what_is_bound_in_it():
    """266 of P04637's 325 models carry a ligand and said nothing about it.

    The flattener reported `in_complex_with` protein partners and dropped
    `ligand_chains` -- zinc and magnesium on the p53 models -- along with
    `oligo-state`, which is the only thing that distinguishes a monomer from
    a 4-mer when there are no protein partners. The summary built its own
    narrower dict than the model list, so it was missing them twice over.
    """
    source = _source("swissmodel_tool.py")
    assert 's.get("ligand_chains")' in source
    assert 's.get("oligo-state")' in source
    assert 'summary["best_model"] = self._flatten_structure(best)' in source


def test_a_living_donor_has_demographics_too():
    """Reading only organ_donor_data returned {} for every living donor.

    HuBMAP stores a deceased donor's attributes under
    `metadata.organ_donor_data` and a living donor's under
    `metadata.living_donor_data`, and the normaliser knew only the first --
    so `demographics` came back empty with nothing to say why.
    """
    source = _source("hubmap_sample_tool.py")
    assert 'metadata.get("living_donor_data")' in source


def test_an_osdr_study_returns_its_protocols():
    """"Full metadata for one OSDR study" without the methods.

    OSD-1 lists eight protocols with their types and their full descriptions,
    and all three fields were dropped, along with the investigator, the
    funding agency and the grant number. `assays` and `files` on that
    endpoint hold only a REST_URL each, so the link is what there is to
    report -- counting the object gave 1 for every study.
    """
    source = _source("nasa_osdr_tool.py")
    assert 'metadata.get("study protocol description")' in source
    assert "def _person" in source
    assert '"assays_url"' in source


def test_an_id_mapping_database_says_both_directions():
    """Mapping has two directions and the listing reported one.

    All 95 databases say whether they can be mapped `from` and `to`, and only
    `from` was read -- so a caller choosing a target database had nothing to
    choose on. 90 of them also carry the URI template that resolves an id in
    that database, which is what having a mapped id is for.
    """
    source = _source("uniprot_idmapping_tool.py")
    assert 'item.get("to", False)' in source
    assert 'item.get("uriLink")' in source


def test_a_gwas_study_says_whether_it_has_summary_statistics():
    """The tool is named after summary statistics and did not report them.

    `summaryStatistics` is the FTP path to the deposited statistics, or the
    literal "NA" when there are none, and the study record dropped it along
    with the discovery sample ("2,095 European ancestry exposed individuals"
    against "42,907 ... unexposed"), the per-ancestry counts, the genotyping
    platform, the paper's title and the gene-environment flag.
    """
    source = _source("gwas_sumstats_tool.py")
    assert 'entry.get("summaryStatistics")' in source
    assert '"has_summary_statistics"' in source
    assert 'entry.get("discoverySampleAncestry")' in source
    schema = json.dumps(
        _config("GWASSumStats_get_trait_studies").get("return_schema") or {}
    )
    assert '"summary_statistics"' in schema
    # The row used to be declared as study_accession and nothing else.
    assert '"reported_trait"' in schema


def test_a_trial_returns_its_secondary_outcomes():
    """NCT04280705 has 4 primary outcomes and 39 secondary ones.

    `ClinicalTrials_get_study` begins "get full details" and read
    primaryOutcomes alone -- while the ClinicalTrialsDetailsTool handler in
    the same module has always read both, and had otherOutcomes commented out
    with no reason given. The description, which enumerated "primary
    outcome", is corrected with the fix rather than left to justify it.
    """
    source = _source("ctg_tool.py")
    assert '_outcomes("secondaryOutcomes")' in source
    assert '_outcomes("otherOutcomes")' in source
    assert "OUTCOMES_PER_SEARCH_ROW" in source
    description = _config("ClinicalTrials_get_study")["description"]
    assert "primary, secondary and other" in description


def test_a_nutrient_value_says_how_it_was_obtained():
    """"Calculated from value per serving size measure" is not a measurement.

    Every nutrient row carried name, value and unit, and the derivation code
    that separates an analysed value from a calculated or imputed one was
    dropped -- along with the USDA nutrient number, which is the identifier a
    name is not.
    """
    source = _source("fooddata_central_tool.py")
    assert 'n.get("derivationDescription")' in source
    assert 'n.get("nutrientNumber")' in source


def test_a_cellxgene_collection_can_be_cited_and_is_not_zero_cells():
    """Two defects in one row.

    `publisher_metadata` carries the journal, the date and the 12 authors of
    the retina atlas, and the row reported the DOI and a contact name, so a
    collection could not be cited from a listing. And `total_cells` was
    `sum(ds.get("cell_count", 0) ...)` over datasets that the listing
    endpoint gives no cell_count for, so it was 0 for every collection --
    which reads as "no cells" rather than "the listing does not say".
    """
    source = _source("cellxgene_discovery_tool.py")
    assert "def _publication" in source
    assert "total_cells = sum(counted) if counted else None" in source
    assert '"datasets_with_cell_count"' in source


def test_an_availability_answer_says_when_the_generic_was_approved():
    """"A generic exists" and "a generic was approved in 2015" differ.

    Drugs@FDA sends the whole submission history with every search result --
    284 rows across one availability check -- and the row the search builds
    dropped it, so neither the availability answer nor the search carried an
    approval date. ADVIL's first ANDA, ANDA206581, was approved 2015-08-03.
    The summary is computed once in the search row and carried down, and the
    full history stays the sibling tool's job, which the output now names.
    """
    source = _source("fda_orange_book_tool.py")
    assert "def _submission_summary" in source
    assert '_submission_summary(result.get("submissions"))' in source
    assert "_SUBMISSION_SUMMARY_KEYS" in source
    assert "submission_history_tool" in source


def test_a_nextstrain_coloring_is_more_than_its_key():
    """"gt" is genotype and "num_date" is date, and the response says so.

    Each coloring carries its own `title` and `type`, and a categorical one
    carries the values the build covers -- zika's `country` has 36 -- paired
    with the colour used to draw it. The summary reported the keys and called
    the list complete, which it was, of the keys.
    """
    source = _source("nextstrain_tool.py")
    assert "def _coloring_values" in source
    assert "COLORING_VALUES_PER_DIMENSION" in source
    schema = json.dumps(_config("Nextstrain_get_dataset").get("return_schema") or {})
    assert '"value_count"' in schema


def test_an_immune_estimate_pairs_by_sample_not_by_position():
    """The correlation was over two lists, not over patients.

    `_immune_estimation` grouped expression records by gene and appended the
    values in response order, then correlated `marker_vals[:n]` against
    `target_vals[:n]` with `n = min(len(a), len(b))` -- two lists built from
    separate groupings, paired by position.

    Measured on brca_tcga: all six markers return a value for every one of
    the first 100 samples in the same order, so the positional pairing was
    in fact correct for that request -- by coincidence, not by construction.
    cBioPortal documents no ordering guarantee for /molecular-data/fetch,
    one missing value would shift every later position, and
    `min(len(a), len(b))` would truncate rather than align. Because the
    sample id was dropped, nothing in the output could show whether the
    pairing had held.

    The sibling handler `_gene_correlation` in this module has always built
    per-sample maps and intersected them ("paired samples only"); this one
    now does too, and reports how many samples the r is over. The field the
    fix needed is the one the sweep flagged as dropped: `sampleId`, on all
    600 records.
    """
    source = _source("timer_tool.py")
    # A substring anchor is no use: `_gene_correlation` already read the
    # sample id, so the name was in the file before the fix. Count it.
    assert source.count('rec.get("sampleId")') == 2
    assert "set(marker_by_sample) & set(target_by_sample)" in source
    assert '"n_paired_samples": len(common)' in source


def test_an_immune_estimate_says_it_used_a_hundred_of_a_thousand_samples():
    """`n_samples: 100` was the cap, and the study has over a thousand.

    The mean and median are over whatever 100 samples cBioPortal lists
    first -- not a random sample -- and nothing in the answer said so. The
    cut is now a parameter with a stated default, the study's own sample
    count is fetched and reported, and the ordering is spelled out.
    """
    source = _source("timer_tool.py")
    assert "SAMPLES_PER_ESTIMATE" in source
    assert "def _get_study_sample_count" in source
    assert "not a random sample" in source


def test_open_genes_says_how_a_gene_is_implicated_not_just_how_often():
    """"Use to assess whether and HOW a gene is implicated in aging", and 57.

    `researches` holds the evidence records -- 57 longevity associations and
    14 lifespan studies for GHR -- and `_evidence_counts` reduced each list
    to its length. No other tool in the family returns the records, so the
    longevity effects, the intervention results, the change types, the model
    organisms and the DOIs were unreachable. The digest reports the distinct
    values per evidence type beside the counts, which answers "how" without
    copying hundreds of records.
    """
    source = _source("open_genes_tool.py")
    assert "def _evidence_digest" in source
    assert "_EVIDENCE_DIGEST_FIELDS" in source
    assert '"evidence_counts"' in source, "the counts stay"
    schema = json.dumps(_config("OpenGenes_get_gene").get("return_schema") or {})
    # The success branch used to declare no properties at all.
    assert '"aging_mechanisms"' in schema
    assert '"evidence_summary"' in schema


def test_a_cath_domain_summary_carries_its_function_and_its_boundaries():
    """A domain is its segments, and its summary dropped both.

    `go_terms` -- with the evidence code that qualifies each and the aspect it
    belongs to -- and `ec_terms` are the functional annotation, and
    `pdb_segments` are the residue ranges that make the domain a domain. The
    summary reported a residue COUNT and the CATH classification. The sibling
    handler `_get_funfam` has always returned `go_terms`.
    """
    source = _source("cath_tool.py")
    assert "def _go_terms" in source
    assert 'data.get("pdb_segments")' in source
    assert 'data.get("ec_terms")' in source
    assert source.count('"go_terms"') >= 2, "both handlers must carry them"



def test_a_spearman_p_value_is_not_rounded_to_zero():
    """`round(p, 6)` reports every p below 5e-7 as 0.0.

    A Spearman r of 0.71 between CD19 and PDCD1 over 100 BRCA tumours has
    p = 1.1e-16, and the tool said `p_value: 0.0` -- a claim no test can
    make. Six SIGNIFICANT figures keeps 1.1e-16 and still shortens
    0.0314159265 to 0.0314159.
    """
    source = _source("timer_tool.py")
    assert "def _p_value" in source
    assert "round(float(pval), 6)" not in source, (
        "decimal rounding flattens a small p-value to zero"
    )


def test_an_interaction_names_the_experiments_behind_it():
    """"Evidence Datasets: complete 466" and not one of their names.

    HumanBase answers 466 datasets for BRCA1-TP53 and 479 for TP53-MDM2,
    each with the database it is (IntAct, BioGRID), the kind of evidence it
    provides and the posterior it contributed. The report fetched all of
    them, counted them, and printed the count -- so "evidence" was a number.
    The strongest are named now, by posterior, with the remainder disclosed.
    """
    source = _source("humanbase_tool.py")
    assert "def _top_evidence_datasets" in source
    assert "EVIDENCE_DATASETS_NAMED" in source


def test_cbioportal_says_which_mutation_profile_it_read():
    """"Mutations" and "Mutations (uncalled)" are different profiles.

    The resolver matched a profile by alteration type, took its id and
    discarded the record -- the name, the datatype (MAF) and the description
    that says the calls came from whole-exome sequencing. An empty mutation
    result means different things in a called and an uncalled profile. It
    also falls back to a naming-convention guess when no profile matches,
    and the caller could not tell a matched id from a guessed one.

    The record goes out through an out-parameter: three tests assert on the
    scalar return of _get_mutation_profile_id. The new fields are on the
    response envelope, which this tool's return_schema does not describe --
    it declares the inner mutation array -- so they are guarded here rather
    than by a schema row.
    """
    source = _source("cbioportal_tool.py")
    assert 'found["resolution"] = "matched"' in source
    assert 'found["resolution"] = "guessed"' in source
    assert '"molecular_profile_resolution": profile_found.get("resolution")' in source


def test_a_trial_with_posted_results_says_so():
    """"Get full details" read protocolSection and nothing else.

    NCT04280705 has a results section: 43 outcome-measure results, 100
    serious adverse events with their organ system and assessment type, 10
    other events above a 5% reporting threshold, a participant flow and 7
    baseline measures. The handler read the protocol -- what the trial set
    out to do -- so a trial with results was indistinguishable from one
    without. The rows belong to the sibling extract_* tools, so what is
    reported here is that they exist, how much is in each, and which tool
    returns it.
    """
    source = _source("ctg_tool.py")
    assert "def _results_summary" in source
    assert '"serious_adverse_events"' in source
    assert "extract_clinical_trial_adverse_events" in source
    schema = json.dumps(_config("ClinicalTrials_get_study").get("return_schema") or {})
    assert '"adverse_event_frequency_threshold"' in schema


def test_alliance_names_the_gene_whose_alleles_these_are():
    """A caller who passed MGI:97490 never saw the word "Pax6".

    The models endpoint carries the gene on every row -- its curie, its
    external id and its display symbol -- and the rows reported the allele
    and the model only, with `query_gene_id` echoing the id back. The symbol
    goes in the metadata once rather than on every row, because the row's
    gene is fixed by the request; the per-row copy is the reason this one was
    flagged and is deliberately not added.

    The field is on the response envelope, which this tool's return_schema
    does not describe (it declares the inner data), so it is guarded here.
    """
    source = _source("alliance_genome_tool.py")
    # `gene.get("geneSymbol")` was already in the file twice before the fix,
    # in other handlers, so the anchor has to be the new assignment.
    assert "gene_reference = {}" in source
    assert '"gene": gene_reference' in source


def test_the_sgd_go_slim_row_carries_the_term_and_not_the_slim_set():
    """Both fields of a row I added in an earlier round were wrong.

    SGD's go_slim entries carry `slim_name` (the name of the slim SET --
    "Yeast GO-Slim", "Macromolecular complex terms"), `display_name` (the
    term, "U4/U6 x U5 tri-snRNP complex"), `go_id` (SGD's internal numeric
    id, 294137) and `link` ("/go/GO:0046540", which holds the GO accession).
    The row read `{"go_id": entry["go_id"], "term": entry["slim_name"]}`, so
    for PRP6 every one of the six rows reported the slim set as the term and
    an internal id as the GO id. Two plausible names over two wrong values,
    which is worse than the omission it replaced.
    """
    source = _source("sgd_tool.py")
    assert 'entry.get("slim_name")' in source, "the slim set is still reported"
    assert '"slim_set": entry.get("slim_name")' in source
    assert '"term": entry.get("display_name")' in source
    assert "def _go_accession" in source
    assert '"go_id": entry.get("go_id")' not in source


def test_a_cancer_hotspot_answer_says_which_hotspot():
    """`is_hotspot: true` and the gene, and not the protein change.

    The handler fetches the annotation summary to read the gene symbol, and
    the canonical transcript consequence in it carries p.V600E, the
    Missense_Mutation classification, the transcript, the exon and the
    SIFT/PolyPhen/AlphaMissense calls. All of it was discarded, so a caller
    knew BRAF had a hotspot at some residue and not which.
    """
    source = _source("genome_nexus_tool.py")
    assert 'canonical.get("hgvspShort")' in source
    assert '"colocated_variant_ids"' in source
    assert '"most_severe_consequence": data.get("most_severe_consequence")' in source



def test_a_guideline_matched_on_a_field_comes_back_with_it():
    """MAGICapp has no search endpoint, so this tool filters the catalogue here.

    It scores a query against five fields -- name, byName, owner,
    institutionName and description -- and the row it returned kept neither
    institutionName nor description. The tool's own description invites a
    query naming an organisation, so a caller could match on WHO or the
    European Stroke Organisation and get back rows that never said which
    body published them, and could not see the text the match was scored on.

    The invariant, rather than a list: every searched field is a returned
    field. A later round adding a sixth to SEARCH_FIELDS cannot reopen this.
    """
    source = _source("magicapp_tool.py")
    import re

    def tuple_of(name):
        block = re.search(rf"^{name} = \((.*?)\)$", source, re.S | re.M)
        assert block, f"{name} is not a plain tuple literal any more"
        return set(re.findall(r'"([^"]+)"', block.group(1)))

    searched, returned = tuple_of("SEARCH_FIELDS"), tuple_of("ROW_FIELDS")
    # description is capped and set by compact(), not carried in ROW_FIELDS.
    returned |= {"description"}
    assert searched <= returned, (
        f"guidelines are matched on {sorted(searched - returned)} and the row "
        "does not carry it"
    )
    # publishDate alone misreads a living guideline: 2015-02-01 against a
    # lastEdit of 2026-11-07 on the first row of the public catalogue.
    assert '"lastEdit"' in source
    assert '"isLatestPublished"' in source
    # The capped description is declared too. Asserted by its own text: a
    # DECLARED row for "description" cannot fail, because the word is a
    # JSON-Schema annotation key.
    schema = json.dumps(_config("MAGICapp_list_guidelines").get("return_schema") or {})
    assert "one of the fields the query is matched against" in schema


def test_a_dandiset_row_says_which_version_its_counts_describe():
    """The search read the published version; the sibling tools read the draft.

    `most_recent_published_version or draft_version` chose the published
    snapshot, so name, asset_count, size_bytes and status described it --
    while DANDI_get_dataset and DANDI_list_assets both request
    `/versions/draft/`. 000036's published version is from 2023-05-15 and its
    draft was modified 2026-02-17, so the two can disagree with nothing in
    the answer to say they might.

    `embargo_status` was flagged with it and is NOT a defect: the API answers
    401 to `?embargoed=true`, so an embargoed dandiset cannot be listed without
    a token and this tool sends none. 300 dandisets sampled, 300 OPEN. A
    constant is not substance, and a field added with a story it cannot support
    is the shape this sweep exists to catch.
    """
    source = _source("dandi_tool.py")
    assert '"version_is_published"' in source
    assert '"draft_asset_count"' in source
    # The note the search returns says so in words, not only in the schema.
    assert "compare draft_asset_count" in source


def test_an_assay_row_says_how_big_the_screen_was():
    """Name and method cannot tell a 125,000-compound screen from an empty one.

    The search row kept aid, name, source, method, targets and has_score.
    PubChem's summary record also carries SIDCount*/CIDCount* -- AID 902 is
    125,394 compounds of which 1,890 were active -- the depositor's own
    SourceID, the tested-target count, the description, and the date the data
    last changed. For a tool whose description offers help "finding screening
    data", the size and the hit rate of the screen are the substance.

    Protocol and Comment reached no tool at all: the sibling summary handler
    did not read them either, and cut Description to its first three
    paragraphs without saying so.
    """
    source = _source("pubchem_bioassay_tool.py")
    assert 'summary.get("Protocol")' in source
    assert 'summary.get("Comment")' in source
    assert "desc[:3]" not in source, "the description is still cut in silence"
    assert source.count('_counts(summary, "CID")') == 2
    assert "def _last_data_change" in source


def test_a_publication_record_keeps_the_id_that_tells_it_apart():
    """The tool warns about duplicate PMIDs and dropped the only key for them.

    RNAcentral can expose several source records for one PMID with different
    citation metadata, which the metadata of this tool has said in so many
    words since the row-axis sweep -- `total_publications` is a record count,
    "not a guaranteed unique PMID count". `pub_id` is RNAcentral's own record
    id and the only field that distinguishes those records, so the warning
    named a problem the caller had no field to act on.
    """
    source = _source("mirna_tool.py")
    assert 'pub.get("pub_id")' in source
    assert "pub_id is the source record id" in source


def test_a_drug_synonym_says_what_kind_of_name_it_is():
    """Aspirin's 80 ChEMBL synonyms are 65 trade names and 3 research codes.

    The profile returned a flat list of strings capped at 15, in ChEMBL's own
    order, which for aspirin is alphabetical: the 15 shown are all obscure
    brands ("8-hour bayer", "Acetosalic acid"), and nothing said that an ATC
    name, a BNF name, an FDA name and three research codes were among the
    other 60. A tool whose description accepts "a drug name ('aspirin',
    'Tylenol')" cannot tell a brand from a lab code without `syn_type`.

    The type counts are taken over every synonym rather than over the capped
    page, so the cap's loss is visible: 75 deduped, 64 of them TRADE_NAME,
    15 shown.
    """
    source = _source("compound_drug_profile_tool.py")
    assert 'synonym.get("syn_type")' in source
    assert '"synonym_type_counts"' in source
    assert '"synonym_count": len(details)' in source


def test_a_membrane_structure_says_how_many_times_it_crosses():
    """`description` was null on all 74 rhodopsin rows; `comments` had the prose.

    OPM's record carries `subunit_segments` on every structure it serves -- 7
    for archaerhodopsin, 21 for the Nanosalina rhodopsin, up to 100 -- which
    for a tool about membrane topology is the first number a caller wants. It
    also carries the species (74/74), the UniProt entry names (71/74), the
    chain the placement was computed for (74/74), and the tilt's uncertainty
    (37/74) beside the thickness's, which the row already returned.

    `comments` is added under its own name rather than filled into
    `description`: a field holding a plausible neighbour's value is the defect
    this file records for DOAJ and SGD, not a fix for one.
    """
    source = _source("membrane_topology_tool.py")
    assert 'o.get("subunit_segments")' in source
    assert '"comments": o.get("comments") or None' in source
    assert '"description": o.get("description")' in source
    assert 'o.get("tilterror")' in source


def test_a_catalytic_residue_is_numbered_the_way_papers_number_it():
    """M-CSA entry 2's catalytic serine is Ser70, and the tool said 45.

    A residue chain carries `resid`, M-CSA's own sequential index, and
    `auth_resid`, the PDB author numbering. For class A beta-lactamase they
    are 45 and 70, and the mechanism text in the same response calls the
    residue "Ser70" twice. The row reported 45 under `residue_number`, for a
    tool whose stated purpose is interpreting active-site mutations: the
    wrong number under the right name, which is worse than no number.

    A role is `{function, function_type, emo}` and the row collapsed it to a
    sorted set of `function` strings, so 38 role records on the first residue
    became a handful of names and `function_type` -- reactant, interaction or
    spectator -- went with them. Two of entry 2's seven residues are
    spectators only.

    `reaction_name` was read from a key M-CSA does not send: the reaction
    object holds ec, compounds, mechanisms and is_polymeric and has never
    carried a name, so the field was null on every entry ever served, while
    the compounds (beta-lactam + water -> substituted beta-amino acids, each
    with its ChEBI id) and both curated mechanisms with their twelve
    references reached nobody.
    """
    source = _source("mcsa_tool.py")
    assert 'first.get("auth_resid")' in source
    assert "def _reference_chain" in source, "the first chain is still assumed"
    assert 'role.get("function_type")' in source
    assert "def _mechanisms" in source
    assert 'reaction.get("name")' not in source, "a key M-CSA does not send"
    assert "MECHANISM_TEXT_CHARACTERS" in source


def test_an_hca_project_says_which_species_and_which_assay():
    """The first project the HCA search returns is mouse.

    `hca_search_projects` returned entryId, projectTitle, organ and
    donorDisease. The hit it already had in hand carries the donors'
    `genusSpecies` -- and the first project this endpoint answers is "1M
    Neurons", Mus musculus -- so a caller filtering for human data took mouse
    projects as human with nothing in the row to check against. It also
    carries `libraryConstructionApproach` ("10x 3' v2"), which for a tool
    that searches *single-cell* projects is the assay identity, the cell
    counts (1,330,000 for that project), the donor ages and count, the
    laboratory, and whether the data is accessible at all.

    `organ` and `donorDisease` were read off `specimens[0]` and
    `donorOrganisms[0]`; a project can have several of each, so they are now
    the union over all of them.

    The file manifest is a list of downloads that could not be verified:
    sha256, version, uuid, and `isIntermediate`, which is how a final matrix
    is told from an intermediate.
    """
    source = _source("hca_tool.py")
    assert '"genusSpecies": _facet(donors, "genusSpecies")' in source
    assert '"libraryConstructionApproach"' in source
    assert 'f.get("sha256")' in source
    assert "def _facet" in source
    assert 'specimens[0].get("organ")' not in source


def test_a_network_edge_carries_what_was_measured_on_it():
    """82 nodes with 378 attributes, 118 edges with 2,222, and none returned.

    NDEx serves CX, where the measurements live in `nodeAttributes` and
    `edgeAttributes` aspects that point at their element with `po`. The
    wrapper read `nodes`, `edges` and `networkAttributes` and skipped both
    attribute aspects, so an AP-MS network came back as a bare topology:
    "ANAPC4 interacts with X" with no Saintscore, BFDR, logOddsScore,
    Entropy or WD. The first edge of the audited network scores Saintscore
    0.07 and BFDR 0.68 -- a low-confidence call that read exactly like a
    high-confidence one.

    CX declares each attribute's type in `d`, so the values are coerced: a
    SAINT score that arrives as the string "0.07" cannot be compared to a
    threshold. Layout coordinates and Cytoscape visual properties are not
    returned, and the metadata says so.
    """
    source = _source("ndex_tool.py")
    assert "def _cx_attributes" in source
    assert '"nodeAttributes" in aspect' in source
    assert '"edgeAttributes" in aspect' in source
    assert "def _cx_value" in source, "attribute values are still strings"
    assert "node_attribute_names" in source


def test_a_domain_search_says_where_on_the_protein():
    """`entries` held the match and the row dropped the whole block.

    `InterPro_get_proteins_by_domain` answers which proteins contain a
    domain, and each hit carries an `entries` block saying where: IPR011615
    runs 106-281 of A0A016WYN1's 439 residues, as a `domain` entry. The row
    returned accession, name, source_database, length, organism and tax id --
    the protein, and nothing about the containment the question was about.

    The location shape is now built by one helper, `_match_locations`, used
    by this endpoint and by its twin `InterPro_get_entries_for_protein`: a
    caller joining a domain's proteins to a protein's domains reads both, and
    the two had no reason to drift.
    """
    source = _source("interpro_ext_tool.py")
    twin = _source("interpro_entry_tool.py")
    assert "def _match_locations" in source
    assert "def _match_locations" in twin
    assert '"match_locations": locations' in source
    assert "locations = _match_locations(protein_rows)" in twin
    assert 'meta.get("gene")' in source
    assert 'matched.get("entry_type")' in source


def test_both_monarch_searches_build_the_same_row():
    """One endpoint, two row builders, six fields against fifteen.

    `Monarch_search_entity` and `Mondo_search_disease` both GET
    `/search`. The general handler's row carries the score, the match type,
    the synonyms, the namespace and the provider; the Mondo one carried id,
    name, category, description, xref and deprecated. So a disease search
    returned ten rows in relevance order with the relevance removed --
    "breast cancer" scores 287.25 against 51.77 for "sporadic breast
    cancer" -- and no way to see that the hit matched a synonym rather than
    the name.

    They now share `_search_row`, which is the fix for the drift rather than
    a second copy of the field list. `xref` is kept beside `xrefs` so the
    Mondo caller's existing key still resolves.
    """
    source = _source("monarch_v3_tool.py")
    assert "def _search_row" in source
    assert source.count('item.get("match_type")') == 1, (
        "the row list is duplicated again"
    )
    assert '"xref": item.get("xref", [])' not in source
    assert 'row["xref"] = row["xrefs"]' in source


def test_a_binding_site_residue_says_which_residue_it_is():
    """1,136 residue codes, and the rows were positions.

    PDBe-KB's residue record carries `startCode`/`endCode` -- the amino acid,
    LYS for P04637's first NAD-binding residue -- and `indexType`, which says
    the index is in UniProt and not PDB numbering. Both handlers returned
    `{start: 382, end: 382, pdb_entries: [...]}`: a number, in tools whose
    descriptions promise "ligand binding site residues" and "interface
    residues".

    `interactingPDBEntries` went too. The paged `pdb_entries` field is
    `allPDBEntries`, every structure covering the residue; the interacting
    list is the subset where the contact is actually seen, with the chains,
    and is the narrower claim a caller wants.

    The ligand itself was thin: no scaffold SMILES, no atom count, and no
    `significance`, which is what the ligand list is ordered by.

    The two handlers are the ligand and protein-protein faces of one endpoint
    family and had duplicated the residue loop, so the row is now one helper.
    """
    source = _source("pdbe_kb_tool.py")
    assert "def _residue_row" in source
    assert source.count('residue.get("startCode")') == 1, (
        "the residue row is duplicated again"
    )
    assert 'residue.get("indexType")' in source
    assert 'residue.get("interactingPDBEntries")' in source
    assert 'additional.get("significance")' in source


def test_a_cell_line_row_says_whether_it_has_knockout_data():
    """Two fields of twenty-four, for a tool offered for target validation.

    A Cell Model Passports /models item carries 24 attributes and the row was
    {model_id, model_name}. Nine of the dropped ones are `*_available` flags:
    PK-59 is crispr_ko_available false and SNU-1033 true, and a caller
    planning a knockout screen could not tell them apart. The measured
    characteristics went too -- mutations_per_mb 24.79 is the tumour
    mutational burden, ploidy_wes 3.51 the ploidy, model_type separates a
    cell line from an organoid.

    The description promised two fields this endpoint does not have. Tissue
    and cancer type live on related sample and patient resources, one request
    per model, which is what DepMap_get_cell_line is for -- so the
    description now says that instead of claiming to return them.
    """
    source = _source("depmap_tool.py")
    assert '"data_available"' in source
    assert 'attributes.get("mutations_per_mb")' in source
    assert 'attributes.get("ploidy_wes")' in source
    description = _config("DepMap_get_cell_lines")["description"]
    assert "data_available" in description
    assert "NOT on this endpoint" in description


def test_a_conservation_status_names_the_authority_that_issued_it():
    """"G4" is a NatureServe rank, and the row said only "G4".

    Both iNaturalist handlers reduced the status object to `cs["status"]`.
    For Danaus plexippus that is "G4" -- a NatureServe global rank, not an
    IUCN category, and the schema called it IUCN. The authority, the place
    and the source URL were dropped, and so were the other 28 statuses the
    same response carries, among them "Special Concern" under the Canadian
    Species at Risk Act.

    `listed_taxa` went entirely: the monarch is `establishment_means:
    "introduced"` in Australia and Guam and native elsewhere, which is a fact
    about the species. iNaturalist returns at most 100 of the 1,588 listings
    it holds, so the response's own cut and this tool's are both reported.
    """
    source = _source("inaturalist_tool.py")
    assert "def _conservation_status" in source
    assert 'status.get("authority")' in source
    assert "def _place_listings" in source
    assert 'listing.get("establishment_means")' in source
    assert "PLACE_LISTINGS_PER_TAXON" in source
    assert '"place_listings_total": r.get("listed_taxa_count")' in source


def test_a_structure_list_says_what_format_and_what_is_in_it():
    """375 structures, a download URL each, and no format to parse them with.

    The row promised "model identifier, provider, category, coverage,
    resolution or confidence, and download URL" and delivered that -- but
    `model_format` says whether the file at that URL is MMCIF or PDB, and 2
    of P04637's 375 models are PDB while 373 are MMCIF. A caller cannot pick
    a parser from the URL.

    `sequence_identity` went too: 9c5s covers p53 at 50 percent and 5mhc at
    100, and both read identically. And the 1,220 entity records across those
    structures -- 640 NON-POLYMER, 579 POLYMER, 1 BRANCHED -- say which
    chains are protein and what ligands are bound, so "which of these has a
    ligand" was unanswerable. The per-structure counts by type are reported
    beside the capped list so that question can be answered without reading
    every entity.
    """
    source = _source("three_d_beacons_tool.py")
    assert 'sm.get("model_format")' in source
    assert 'sm.get("sequence_identity")' in source
    assert "def _entities" in source
    assert "ENTITIES_PER_STRUCTURE" in source
    assert '"entity_counts_by_type": entity_counts' in source


def test_both_finngen_handlers_report_the_same_phenotype():
    """gc_lambda was on the lookup and not on the list, from one record shape.

    FinnGen's /phenos list carries `gc_lambda` -- the genomic-control
    inflation factor at four quantiles -- on all 2,470 phenotypes, and
    `assoc_files`, the summary statistics behind each. The list row returned
    six fields and dropped both, while the single-phenotype handler next to
    it already returned gc_lambda from the same shape. For a list whose
    purpose is picking a GWAS to analyse, lambda is the "is this usable"
    reading: AB1_TUBERCULOSIS_MILIARY is 0.38 at the 0.5 quantile.

    Both now build `_phenotype_row`, and the previous-release counts stay
    conditional because only the per-phenotype endpoint sends them.
    """
    source = _source("finngen_tool.py")
    assert "def _phenotype_row" in source
    assert source.count('record.get("gc_lambda")') == 1, (
        "the phenotype row is duplicated again"
    )
    assert 'record.get("assoc_files")' in source
    assert '"num_cases_prev"' in source


def test_a_substance_name_says_which_pharmacopoeia_lists_it():
    """A name's `references` are uuids, and the citations were never resolved.

    GSRS gives each name and code a `references` list of uuids that point
    into the record's own `references` array, where the citation lives: "EP
    6.5" with docType FDA_SRS. Aspirin's record carries 78 of them and the
    tool returned none, although the module docstring above the class
    promises "regulatory references from the ?view=full record". The uuids
    alone are useless, which is why resolving them -- rather than passing
    them through -- is the fix.

    A code's `comments` went with them, and for WHO-ATC that is the
    classification path the code stands for: C07FX02 is
    "ATC|CARDIOVASCULAR SYSTEM|BETA BLOCKING AGENTS|...". The names also lost
    their jurisdictions, languages and standardised forms.

    An entry whose reference uuid is not inlined in the record is reported as
    the bare uuid rather than dropped, so the caller can see that a citation
    exists and could not be resolved.
    """
    source = _source("fda_gsrs_tool.py")
    assert "def _reference_index" in source
    assert "def _citations" in source
    assert 'c.get("comments")' in source
    assert 'n.get("nameJurisdiction")' in source
    assert "CITATIONS_PER_ENTRY" in source
    assert '"total_references": len(reference_index)' in source


def test_a_phenotype_annotation_carries_the_ontology_term():
    """MGI_get_phenotypes names MP in its description and returned no MP id.

    Every one of the 125 annotations on MGI:97490 carries
    `{"curie": "MP:0005193", "name": "abnormal anterior eye segment
    morphology", "definition": ...}`, and the row returned
    `phenotype_statement` -- the same words as free text -- with no term and
    no identifier, so a phenotype could not be joined to any ontology tool.

    Two relations were dropped and they are different claims: the row's is
    "is_implicated_in" and each annotation's is "has_phenotype". So were the
    data provider, which matters because the Alliance aggregates several, and
    `phenotypeAnnotationSubject.primaryExternalId` -- the genotype the
    phenotype was observed in, MGI:2170872, which is not the queried
    MGI:97490.

    ZFIN and WormBase compose free-text statements instead of annotating a
    single term, so `phenotype_terms` is empty for them by upstream design:
    0 terms across 18 WormBase rows and 2 ZFIN rows against 125 of 125 for
    MGI.
    """
    source = _source("alliance_genome_tool.py")
    assert "def _phenotype_terms" in source
    assert 'annotation.get("phenotypeTerms")' in source
    assert "def _annotation_facet" in source
    assert '"relation": (r.get("relation") or {}).get("name")' in source
    assert '("dataProvider", "abbreviation")' in source
    assert '("phenotypeAnnotationSubject", "primaryExternalId")' in source


def test_a_supplement_label_carries_its_precautions():
    """"Full label" returned the ingredient table and none of the warnings.

    NIHDSLD_get_label promises "one dietary supplement's full label". The
    audited product's label carries 23 statements, each with the type that
    says what kind it is, and four are precautions: "Precautions re: Pregnant
    or Nursing or Prescription Medications", "KEEP OUT OF THE REACH OF
    CHILDREN", "Take only as directed. Do not exceed suggested dosage." and
    "Do not use if inner seal is broken or missing." None of them reached the
    caller. Without `type`, a precaution would read like a marketing line,
    which is why both are returned.

    The description also promises "every ingredient", and the 9 other
    (inactive) ingredients -- glucose syrup, sucrose, gelatin -- were absent,
    as was `percentDvFootnote`, which says what the percent daily values the
    tool does return are a percentage of. `off_market: true` was reported
    with no date, though the label's events say 2018-01-19.
    """
    source = _source("nih_dsld_tool.py")
    assert "def _statements" in source
    assert "def _other_ingredients" in source
    assert 'payload.get("percentDvFootnote")' in source
    assert "STATEMENTS_PER_LABEL" in source
    assert '"events"' in source


def test_a_trait_search_says_which_scores_not_how_many():
    """A polygenic score catalogue returned `n_scores: 88` and no ids.

    `PGSCatalog_search_traits` exists to find the scores for a trait, and the
    response it already had in hand carries them: `associated_pgs_ids` holds
    88 for MONDO_0005010. A count plus a sibling that takes the trait_id
    would be a fair split -- except that `child_associated_pgs_ids` holds 8
    more, attached to child terms, and measured live not one of them is
    returned by `score/search?trait_id=MONDO_0005010`. Those 8 were reachable
    through no call this tool makes.

    `trait_synonyms` went too, and it is what explains a match: the query
    "coronary artery disease" is a synonym of the label the row reports,
    "coronary artery disorder".
    """
    source = _source("pgs_catalog_tool.py")
    assert 't.get("associated_pgs_ids")' in source
    assert 't.get("child_associated_pgs_ids")' in source
    assert 't.get("trait_synonyms")' in source
    assert "PGS_IDS_PER_TRAIT" in source
    note = _config("PGSCatalog_search_traits")
    assert "child_associated_pgs_ids" in json.dumps(note.get("return_schema"))


def test_a_disease_gene_evidence_code_keeps_its_identifier():
    """IEP and ECO:0000270 were reduced to the prose that describes them.

    Alliance sends each evidence code as `{"curie": "ECO:0000270",
    "abbreviation": "IEP", "name": "expression pattern evidence used in
    manual assertion"}`. The row kept the name, so neither the three-letter
    code a paper cites nor the ECO id a machine reads reached the caller.

    The annotation relation went with them, and it is the claim itself:
    "is_implicated_in" and "is_marker_for" come back 35 and 23 times on one
    page of DOID:162 and mean different things about a gene-disease link. The
    data provider -- RGD on 57 of 58, OMIM on one -- was dropped as well.

    `negated` is carried as a count. None of the 58 annotations measured is
    negated, so it is latent here; the same field on GO associations was
    returning genes curated against the function they were listed under,
    which is why it is reported rather than assumed absent.
    """
    source = _source("alliance_genome_tool.py")
    assert "def _evidence_codes" in source
    assert '"abbreviation": term.get("abbreviation")' in source
    assert '"negated_annotations"' in source
    assert source.count('("relation", "name")') >= 2


def test_a_thesaurus_concept_says_which_synonym_is_its_name():
    """Ten of seventeen synonyms claim "PT" and only one is NCIt's name.

    An NCIt synonym carries two different type fields. `termType` is the
    term's role within its SOURCE terminology, and C3224 (Melanoma) has ten
    rows with termType "PT" -- CDISC's is "MELANOMA, MALIGNANT". NCIt's own
    name is on the single row whose annotation property is `Preferred_Name`,
    and that row carries no termType, so the old row reported it as
    `{"name": "Melanoma", "type": null, "source": null}`: the one
    authoritative name, indistinguishable from noise.

    The annotation property and its P-code are now returned beside termType,
    with the preferred and display rows flagged. Property codes are carried
    for the same reason: `type` is the label and `code` is what NCIt's
    downstream datasets key on.
    """
    source = _source("nci_thesaurus_tool.py")
    assert 's.get("typeCode")' in source
    assert '"is_preferred_name": s.get("type") == "Preferred_Name"' in source
    assert '"code": p.get("code")' in source
    # termType is still what `type` holds, so no caller's key changes meaning.
    assert '"type": s.get("termType")' in source


def test_a_population_says_what_data_exists_for_it():
    """The sample search read dataCollections; the population search did not.

    An IGSR population record carries ten data collections, each naming its
    data types ("alignment", "variants"), the sequencing behind them
    ("PCR-free high coverage") and the document governing reuse. The
    population row returned the code, name, description, sample count,
    superpopulation and coordinates -- nothing about whether the population
    has usable data. `IGSR_search_samples`, in the same module, already read
    the same block for its titles alone.

    `overlappingPopulations` went with it, which is how IGSR records that two
    population codes cover the same people.
    """
    source = _source("igsr_tool.py")
    assert "def _data_collections" in source
    # Both handlers call the one reader, and `data_collections` means the
    # titles in both: the sample handler already used that name for them and
    # its schema declares an array of strings, so the rich records took a
    # name of their own rather than giving one key two shapes.
    assert source.count("_data_collections(src)") == 2
    assert '"data_collection_details": _data_collections(src)' in source
    assert 'collection.get("dataReusePolicy")' in source
    assert '"overlapping_populations"' in source


def test_the_third_interpro_endpoint_also_says_where():
    """Two endpoints of this family were fixed before this one was looked at.

    `entries_for_protein` gained its match locations in round 26 and
    `proteins_by_domain` in round 29, each from the same
    `entry_protein_locations` block. `structures_for_domain` lives in a
    different module and was not looked at either time: it answered which PDB
    structures contain PF00870 and nothing about the containment -- not the
    chains (A and C for 1gzh), not the residues, not the 6.8e-60 e-value.

    This endpoint has a frame the other two do not.
    `entry_structure_locations` is in the structure's own numbering with
    `auth_start`/`auth_end` beside it: 6-194 and auth 100-288 for the same
    domain whose UniProt range is 100-288. Both frames are returned, because
    a caller holding a PDB residue number and a caller holding a UniProt one
    need different ones.
    """
    source = _source("interpro_domain_arch_tool.py")
    assert "def _domain_locations" in source
    assert 'fragment.get("auth_start")' in source
    assert '"entry_protein_locations"' in source
    assert '"entry_structure_locations"' in source
    assert '"chains"' in source


def test_a_network_search_says_what_the_networks_are_of():
    """Round 29 fixed the single-network attributes and missed the search.

    `NDEx_search_networks` returned the uuid, name, owner, counts and a
    300-character description, and dropped `properties` -- where NDEx keeps
    what a caller actually chooses a network by. The first BRCA hit carries
    organism "Homo sapiens", disease "cancer", tissue "breast carcinoma" and
    methods "coexpression analysis"; the second carries an ARACNe
    non-commercial licence and its citation, so a caller could have used a
    restricted network without seeing the restriction.

    Values are coerced by the `dataType` NDEx declares, the same treatment
    the node and edge attributes got in round 29, and the description cut is
    now disclosed rather than silent.
    """
    source = _source("ndex_tool.py")
    assert "def _network_properties" in source
    assert 'row.get("predicateString")' in source
    assert '"description_truncated"' in source
    assert "DESCRIPTION_CHARACTERS" in source
    # The summary handler built `str(value)[:300]` for the same block, so a
    # numeric property reached one caller as a number and the other as a
    # truncated string. One reader now.
    assert source.count("_network_properties(") == 3
    assert 'str(p.get("value", ""))[:300]' not in source
    # `properties` is a JSON-Schema keyword, so a DECLARED row for it cannot
    # fail; assert the declaration by the text that is unique to it.
    schema = json.dumps(_config("NDEx_search_networks").get("return_schema") or {})
    assert "the fields a caller picks a network BY live" in schema


def test_a_clinvar_conflict_comes_with_its_submissions():
    """"Conflicting classifications of pathogenicity" and nothing to weigh it.

    GeneBe returns BRAF V600E as ACMG Pathogenic with
    `clinvar_classification: "Conflicting classifications of pathogenicity"`.
    The record also carries `clinvar_review_status: "criteria provided,
    conflicting classifications"` and `clinvar_submissions_summary: "P:3 LP:1
    US:5 O:1"` -- five of the ten submissions call it uncertain -- and the
    row reported the conflict with neither, which is a conflict a caller
    cannot act on.

    `consequences` went entirely. The variant is annotated on 43 transcripts
    and the row reported one `transcript` string, with nothing saying which
    is MANE Select (NM_004333.6 / ENST00000646891.2) or what the biotype of
    each is. They are returned MANE-first, capped, with the count disclosed.

    The batch handler in this same module returns the raw variant record
    whole, so none of this cost a request: the projection was a choice.
    """
    source = _source("genebe_tool.py")
    assert '"clinvar_review_status"' in source
    assert '"clinvar_submissions_summary"' in source
    assert "def _consequences" in source
    assert '"mane_select"' in source
    assert "CONSEQUENCES_PER_VARIANT" in source
    assert '"consequences_truncated"' in source


def test_an_osdr_hit_carries_the_study_description():
    """A study search whose rows a caller has to choose between, with no text.

    OSDR's hit carries `Study Description` -- "Exposure to microgravity
    causes bone loss in humans..." -- and the row dropped it, along with
    `Study Assay Technology Platform`. That platform is often the only one of
    the three assay fields populated: on the first microgravity hit
    `Study Assay Technology Type` is the empty string while the platform
    reads GPL1219, so the row reported a null assay type and discarded the
    field that would have answered.

    The declaration is asserted by its own text rather than by a membership
    test, because `"description"` is a JSON-Schema annotation key and occurs
    in every schema that documents anything.
    """
    source = _source("nasa_osdr_tool.py")
    assert 'source.get("Study Description")' in source
    assert "DESCRIPTION_CHARACTERS" in source
    schema = json.dumps(_config("OSDR_search_studies").get("return_schema") or {})
    assert '"description": {"type": ["string", "null"], "description": "What the study was' in schema


def test_the_cna_path_names_its_profile_like_the_mutation_path():
    """Round 26 fixed one path of this module and left the other.

    `_resolve_molecular_profile_id` takes a `found` out-parameter, and round
    twenty-six used it on the mutations path so a caller learns which profile
    the calls came from and whether the id was matched against the study's
    profile list or guessed from the naming convention. `_get_cna_profile_id`
    never passed it, so the copy-number path reported `brca_tcga_gistic` and
    nothing else -- and the profile's own description is where the value
    legend lives: "-2 = homozygous deletion ... 2 = high level
    amplification". Without it the integers in `data` cannot be read.

    The guard counts occurrences, because the mutations path has had both
    lines since round 26 and a substring test would have passed against the
    unfixed CNA path.
    """
    source = _source("cbioportal_tool.py")
    assert source.count("found=profile_found") == 2
    assert source.count('"molecular_profile": profile_found.get("profile")') == 2
    assert (
        source.count('"molecular_profile_resolution": profile_found.get("resolution")')
        == 2
    )


def test_an_api_registry_hands_over_the_production_server():
    """`servers[0]["url"]` was a development endpoint for a real entry.

    A SmartAPI entry declares several servers, each with an `x-maturity` of
    production, staging or development, and the array order is not the order
    of usefulness. The CFDE Gene Regulation Linked Data Hub lists
    https://genboree.org/cfde-gene-dev first and
    https://genboree.org/cfde-gene second, so the row handed a caller the
    development endpoint as the API's base url with nothing saying so. That
    is a wrong value rather than a missing one, which is why the fix changes
    which url `base_url` holds rather than only adding fields.

    `base_url_maturity` makes the choice visible, and an entry whose ONLY
    server is a development one -- Translator Gene Clustering is -- now says
    so instead of passing it off as the API.

    `info.contact` was already in `_SEARCH_FIELDS` and never read, so the
    registry's answer to "who maintains this" was fetched and discarded on
    every search. It is returned with the email the registry publishes for
    that purpose: this is an API's own support contact, unlike the specimen
    collectors' addresses this sweep left out of iDigBio.
    """
    source = _source("smartapi_tool.py")
    assert "def _base_url" in source
    assert 'server.get("x-maturity")' in source
    assert '"production", "staging"' in source
    assert "def _servers" in source
    assert '"contact": _contact(info)' in source
    assert 'servers[0].get("url") if servers else None' not in source


def test_a_concept_definition_says_who_wrote_it():
    """Four definitions for Melanoma, and `definitions[0]` is the glossary one.

    C3224 carries definitions from NCI-GLOSS, CDISC, NICHD and NCI, in that
    order. The row returned the first -- the patient-facing glossary text --
    as the concept's definition, with no source, while the thesaurus's own
    NCI definition sat fourth. Which body wrote a definition is part of what
    the definition is.

    The NCI-sourced one is preferred now, its source is reported, and all
    four are returned beside it. This was found by grepping the module for
    `[0]` after the SmartAPI base_url finding, not by a shard: the same
    module's synonyms had been fixed one round earlier and this sat two
    screens above them.
    """
    source = _source("nci_thesaurus_tool.py")
    assert 'row.get("source")' in source
    assert '"definition_source"' in source
    assert '(row.get("source") or "") == "NCI"' in source
    assert 'definitions[0].get("definition")' not in source


def test_an_expression_annotation_carries_its_anatomy_ids():
    """"anal fin" at "Larval:Days 14-20", and no ontology id for either.

    The record behind that row carries UBERON:0000026 and UBERON:0001062 in
    `termIds`, and ZFA:0001162 -- the species-specific anatomy term -- under
    `expressionPattern.whereExpressed.anatomicalStructure`. The two are not
    the same set, so both are returned: `term_ids` and `uberon_term_ids` for
    the slim ids, `anatomical_structure_curie` for the ZFA one.

    `expressionAssayUsed` went too. "RNA in situ" (MMO:0000658) is a
    different weight of evidence from a sequencing assay, and the row said
    neither. So did `crossReferences`, which for ZFIN is the FIGURE the call
    was read off; its resolver template is in the same record, so the link is
    built rather than guessed.

    The nested `expressionPattern` object is not returned whole: it repeats
    the strings the row already has and nests four levels deep. The two
    fields worth having are extracted from it.
    """
    source = _source("alliance_genome_tool.py")
    assert 'r.get("termIds")' in source
    assert 'r.get("uberonTermIds")' in source
    assert "def _expression_pattern" in source
    assert '"anatomical_structure_curie"' in source
    assert 'ann.get("expressionAssayUsed")' in source
    assert "def _cross_references" in source
    assert '"expression_pattern": ann.get("expressionPattern")' not in source


def test_a_proteomics_tool_points_at_the_spectrometry_evidence():
    """36 features, and no link to a single mass-spectrometry dataset.

    `proteins_api_get_proteomics` promises "proteomics data for a protein
    including mass spectrometry evidence". UniProt's proteomics endpoint is
    unavailable, which the tool already discloses, so it reads the protein
    entry and keeps its PTM comments and modified-residue features. That
    entry also lists 780 cross-references, of which 21 are the proteomics
    ones -- PeptideAtlas, MassIVE, jPOST, eleven ProteomicsDB entries,
    PhosphoSitePlus, SwissPalm, iPTMnet, GlyGen -- and all 780 were
    discarded, so the tool promised the evidence and returned no route to it.

    The named set keeps the output focused: 780 references become the 21 that
    are about proteomics, each with the properties the entry records, such as
    GlyGen's "27 sites, 13 N-linked glycans (3 sites), 6 O-linked glycans".
    """
    source = _source("proteins_api_tool.py")
    assert "PROTEOMICS_DATABASES" in source
    assert "def _proteomics_cross_references" in source
    assert '"proteomics_cross_references": cross_references' in source
    assert '"PeptideAtlas"' in source


def test_a_taxonomy_search_shows_the_name_it_matched():
    """Round 26 gave the per-taxon lookup its synonyms and not the search.

    The note round twenty-six left said UniProtTaxonomy's description calls
    itself "essential for cross-referencing species", and that taxon 9606
    answers "human" plus sixteen variants that reached no caller. That fix
    landed on `_get_taxon`; `_search`, ninety lines down the same module,
    kept seven fields and none of them was `otherNames`.

    It matters most for the hits a caller did not expect: the query "human"
    returns Homo sapiens subsp. 'Denisova', which matched through its own
    other names -- "Denisovan", "Homo sp. Altai" -- and the row showed a
    scientific name with no indication of why it was there. `active` and the
    parent taxon went with them.
    """
    source = _source("uniprot_taxonomy_tool.py")
    # Three reads: the per-taxon lookup's one, and the search's list
    # comprehension plus its count. Counting rather than testing for the
    # substring, because the lookup has carried it since round 26.
    assert source.count("otherNames") == 3, "the search handler lost its read"
    assert "OTHER_NAMES_PER_SEARCH_ROW" in source
    assert '"parent_taxon_id"' in source
    assert '"active": item.get("active")' in source


def test_an_assembly_can_reach_its_scaffolds():
    """25 chromosomes returned of 194 top-level regions, and 169 unreachable.

    `Ensembl_get_assembly_info` filters `top_level_region` to the
    chromosomes, and it already reported `total_regions: 194` against
    `total_chromosomes: 25` -- so the cut was disclosed, which is why this is
    not the row-axis defect it looks like. The problem is that no tool in the
    family returned the other 169: a caller needing the length of
    KI270728.1, GRCh38's longest scaffold at 1,872,759 bases, had the count
    and no route.

    `coord_system` is now on every region too. The filter reads it, and a
    region admitted through the karyotype branch rather than the
    coord_system one was indistinguishable from a chromosome.
    """
    source = _source("ensembl_info_tool.py")
    assert "OTHER_REGIONS_PER_ASSEMBLY" in source
    assert '"coord_system": region.get("coord_system")' in source
    assert '"total_other_regions"' in source
    assert '"other_regions_truncated"' in source


def test_a_study_condition_keeps_its_mesh_code():
    """Ten synonyms of one condition, and not the code they are synonyms of.

    dbGaP's FHIR CodeableConcepts expand every MeSH term into its entry
    terms, so phs000681's `condition` is 34 entries: one real coding --
    D003924, "Diabetes Mellitus, Type 2", under the MeSH OID -- and 32
    synonym rows whose own `code` is a sentence ("D003924 entry term:
    Adult-Onset Diabetes Mellitus"). `_unique_texts` was written for exactly
    that and says so in its docstring.

    What it left behind was the identifier. The row returned ten near-identical
    strings and no code, so a study's condition could not be joined to MeSH --
    nor to UMLS, whose CUI C0011860 is the second real coding in the same
    list. Entry-term pseudo-codings are excluded by system, which is what
    keeps the output to the two that are identifiers.
    """
    source = _source("dbgap_tool.py")
    assert "def _concept_codes" in source
    assert "_ENTRY_TERM_SYSTEM_MARKER" in source
    assert source.count("_concept_codes(") == 4, "one handler still omits it"


def test_a_region_hit_says_which_genes_the_deletion_removes():
    """A pathogenic 30 kb loss, reported as a span and a title.

    `ClinVar_search_by_region` finds variants overlapping a region, including
    large CNVs, and returned variation_id, title, coordinates, span and
    classification. The esummary record it already had also carries `genes`:
    the 30,531-base loss over chr7:155593770 removes SHH, and the
    668,505-base one removes five genes including EN2 and INSIG1. ClinVar
    147398 lists 696. Which genes a deletion removes is the question a span
    only hints at.

    Each gene now carries its NCBI Gene id -- the field a caller joins on --
    and `source`, which says whether the submitter asserted the gene or
    ClinVar calculated it from the coordinates. The accession (VCV001807779)
    and the review status came back with them, so the record can be cited and
    its classification weighed.
    """
    source = _source("clinvar_tool.py")
    assert "def _gene_rows" in source
    assert 'gene.get("geneid")' in source
    assert 'gene.get("source")' in source
    assert "GENES_PER_OVERLAP_ROW" in source
    assert '"accession": rec.get("accession")' in source


def test_a_phenotype_call_comes_with_the_measurement_behind_it():
    """"competitive fitness: normal" -- on what evidence?

    `SGD_get_phenotypes` returned the phenotype, the mutant type, the
    experiment type and the reference, which is the call and its provenance
    but not its content. SGD records a note on the annotation and another on
    the experiment, and the note is where the number lives: under
    `competitive fitness: normal` the note reads "Relative fitness score:
    1.000", under `haploproficient` it reads "Relative growth score:
    0.0044", and under `cellular morphology: abnormal` it reads "large
    budded cells with nuclei situated at the mother-bud neck".

    For POL3 (S000002260) 22 of the 50 returned annotations carry one. The
    experiment note says how the assay was run ("mutants grown in 96-well
    microtiter plates"), which is what tells a reader whether two
    "decreased" calls are comparable.

    `experiment_properties` was declared as a bare array; its rows have a
    shape (class_type, role, name, value, unit) and now say so.
    """
    source = _source("sgd_tool.py")
    assert '"note": p.get("note")' in source
    assert '"experiment_note"' in source
    assert 'p.get("experiment_details")' in source
    schema = _config("SGD_get_phenotypes")["return_schema"]
    rows = (schema.get("oneOf") or [schema])[0]["items"]["properties"]
    assert "class_type" in rows["experiment_properties"]["items"]["properties"]
    assert "Relative growth score" in rows["note"]["description"]


def test_a_cell_lines_references_are_the_papers_not_the_pointers():
    """83 references, each an opaque internal id.

    `cellosaurus_get_cell_line_info` returned the cell-line record as
    Cellosaurus sends it, and in that record `reference-list` is 83 entries
    of the form {"resource-internal-ref": "CelloPub=CLPUB00047"}. The
    records those point at travel in a sibling block of the same response,
    `Cellosaurus.publication-list`, which the wrapper dropped. A caller
    asking which papers describe HeLa got 83 pointers into nothing.

    They now resolve: CLPUB00047 is "Tissue culture studies of the
    proliferative capacity of cervical carcinoma and normal epithelium.",
    Cancer Res. 1952 -- the paper that established the line. Each record
    carries its authors, journal, volume and pages, and its PubMed id and
    DOI under cross_references. A pointer with no matching record is
    reported as its bare internal id rather than silently dropped, and
    `publication_count` counts the references the cell line holds so a
    truncated list can be recognised as one.
    """
    source = _source("cellosaurus_tool.py")
    assert "def _cell_line_publications" in source
    assert "publication-list" in source
    assert "resource-internal-ref" in source
    assert "PUBLICATIONS_PER_CELL_LINE" in source
    assert "AUTHORS_PER_PUBLICATION" in source
    schema = _config("cellosaurus_get_cell_line_info")["return_schema"]
    props = (schema.get("oneOf") or [schema])[0]["properties"]
    assert "publications" in props
    assert "internal_id" in props["publications"]["items"]["properties"]
    # The passthrough record's own keys were undeclared too: the comment
    # list carrying Cellosaurus's contamination warnings, the STR profile
    # that authenticates the line, 233 cross-references.
    data = props["data"]["properties"]
    for key in ("comment-list", "str-list", "xref-list", "reference-list"):
        assert key in data, key
    assert "publications" in data["reference-list"]["description"]


def test_a_photo_url_says_whether_the_photo_may_be_used():
    """Three Monarch observations, three different copyright positions.

    `iNaturalist_search_observations` returned `photo_url`, the first
    photo's URL, and nothing about its terms. iNaturalist photographers keep
    their own copyright: of three consecutive Danaus plexippus observations
    one photo was "(c) elliottbucknall100, all rights reserved", one "(c)
    Michelle W., some rights reserved (CC BY)" and one all rights reserved
    again. The URLs are indistinguishable -- all three resolve, and nothing
    in the reply said that reusing the first would infringe.

    Every photo now comes with the attribution line its licence requires and
    its `license_code`, which is null exactly when the photographer reserved
    all rights. `photo_count` says how many the observation holds, since only
    the first was ever returned.

    The taxon search had the same shape of gap in a different place: a search
    for "monarch" returns Danaus plexippus (iconic 47158, Insecta) and
    Monarchidae, the Monarch Flycatchers (iconic 3, Aves), and the lineage is
    what separates them. The search endpoint sends the path as ids only, so
    `ancestor_ids` is the path, each id accepted back by
    `iNaturalist_get_taxon`.
    """
    source = _source("inaturalist_tool.py")
    assert "def _photos" in source
    assert 'photo.get("license_code")' in source
    assert 'photo.get("attribution")' in source
    assert "PHOTOS_PER_OBSERVATION" in source
    assert '"photo_count": len(photos)' in source
    assert 'r.get("ancestor_ids")' in source
    # One reader, used by the one handler that has photos.
    assert source.count("_photos(obs)") == 1
    obs = _config("iNaturalist_search_observations")["return_schema"]
    photos = (obs.get("oneOf") or [obs])[0]["items"]["properties"]["photos"]
    assert "all-rights-reserved" in photos["description"]
    assert "license_code" in photos["items"]["properties"]
    taxa = _config("iNaturalist_search_taxa")["return_schema"]
    rows = (taxa.get("oneOf") or [taxa])[0]["items"]["properties"]
    assert "Monarch Flycatchers" in rows["ancestor_ids"]["description"]


def test_a_disorder_annotation_carries_the_sentence_it_rests_on():
    """26 of p53's regions bind something. Which something?

    `DisProt_get_entry` promises "detailed disorder region annotations" and
    that "every region retains all returned cross-references". It returned
    the term name, the evidence code's sentence-long name, the span and the
    PDB/BMRB cross-references -- and dropped, for all 63 of P04637's
    regions, the part a curator writes:

    * `statement`, the sentence from the paper the annotation rests on. One
      binding region's reads "This short helix interacts with the surface of
      Tfb1 formed by beta strands b5, b6, and b7 and the loop connecting b5
      to b6." The term name for that region is `protein binding`.
    * `interaction_partner` for 28 of the 63 -- including 26 annotated
      `protein binding`, where the partner IS the annotation. That same
      region binds UniProt P32776, a cross-reference the description claimed
      to retain.
    * `reference_id` and `reference_source`: a PubMed id for every region
      (16793543 for that one), so the annotation can be followed to its
      paper.
    * `ec_id`, the ECO identifier, where only `ec_name` was returned -- an
      identifier reduced to its own description.
    * `curator_name`, `curator_orcid` and the annotation date.

    One field went the other way: `method` was read from `method_name`,
    which DisProt does not send on this endpoint -- 0 of 63 regions
    populate it. A key that is always null is not a disclosure, so it is
    gone.
    """
    source = _source("disprot_tool.py")
    assert "def _statements" in source
    assert "def _partners" in source
    assert "STATEMENT_CHARACTERS" in source
    assert 'region.get("ec_id")' in source
    assert 'region.get("reference_id")' in source
    assert 'region.get("curator_orcid")' in source
    # The key the API never answers is not read any more.
    assert 'region.get("method_name")' not in source
    schema = _config("DisProt_get_entry")["return_schema"]
    rows = (schema.get("oneOf") or [schema])[0]["properties"]["regions"][
        "items"
    ]["properties"]
    assert "method" not in rows
    assert "protein binding" in rows["interaction_partners"]["description"]
    assert "ECO:0006165" in rows["evidence_code_id"]["description"]


def test_a_cluster_is_its_membership():
    """member_count: 254. Members returned: 1.

    `UniRef_get_cluster` fetched UniRef90_P05067, whose reply carries 253
    member records -- each with its UniProtKB accessions, organism, protein
    name, and its UniRef50, UniRef100 and UniParc ids -- and returned the
    representative member alone. The count was there, the membership was
    not, and no sibling tool takes a cluster id: `UniRef_search_clusters`
    searches by text. So the 253 sequences the cluster groups had no path to
    any caller, from a reply the wrapper had already paid for.

    Members now come back capped at MEMBERS_PER_CLUSTER with
    `members_truncated` saying when the cap applied, and
    `members_in_response` beside `member_count` because the two differ by
    one: the count includes the representative, which is reported
    separately.
    """
    source = _source("uniref_tool.py")
    assert "def _member" in source
    assert "MEMBERS_PER_CLUSTER" in source
    assert 'member.get("accessions")' in source
    assert 'member.get("uniparcId")' in source
    assert '"members_truncated"' in source
    schema = _config("UniRef_get_cluster")["return_schema"]
    props = (schema.get("oneOf") or [schema])[0]["properties"]
    assert "254" in props["members"]["description"]
    assert "accessions" in props["members"]["items"]["properties"]


def test_the_tool_that_promises_factors_reports_the_factors():
    """"Returns experiment metadata and factor information" -- 29 of them,
    as the number 29.

    `GxA_get_experiment_info` returned `total_conditions`, a count, and
    `column_groupings`, which the Atlas sends empty for E-MTAB-2836. Its
    `columnHeaders` block holds the 29 assay groups with their factor
    values, ontology terms, replicate counts and sample properties -- and
    `contrastPropertyType` on each property, which is what separates the
    characteristic the experiment varies (`organism part`, FACTOR) from the
    ones held fixed (`developmental stage`, `organism`, `sex`, SAMPLE).

    The sibling expression handler in the same module already read all of
    it. This is drift between two handlers over one block, so there is now
    one reader, `_column`, and both call it.
    """
    source = _source("gxa_tool.py")
    assert "def _column" in source
    assert 'prop.get("contrastPropertyType")' in source
    # One reader: the expression handler and the info handler both use it.
    assert source.count("_column(col)") == 2
    schema = _config("GxA_get_experiment_info")["return_schema"]
    props = (schema.get("oneOf") or [schema])[0]["properties"]
    assert "FACTOR" in json.dumps(props["conditions"])
    assert "count" in props["conditions"]["description"]


def test_the_ndc_tool_answers_for_a_prescription_drug_too():
    """"a drug's active ingredient ... and National Drug Code (NDC) number".

    `FDA_get_manufacturer_name_NDC_number_by_drug_name` returned
    `active_ingredient` and `openfda.product_ndc`. Measured on the live API,
    `active_ingredient` is an OTC-only SPL section: populated on 99 of 100
    HUMAN OTC DRUG labels and on 0 of 100 HUMAN PRESCRIPTION DRUG labels.
    So for every prescription drug the tool answered its own headline
    promise with null, while the same record carried
    `openfda.substance_name` and `openfda.unii` -- populated on 99 of those
    100 labels.

    "The NDC number" also has two levels and only one was returned. The
    product NDC (70771-1859) identifies the product; the package NDC
    (70771-1859-6) is what is printed on the carton and what pharmacy and
    claims data key on. Prescription labels carry a median of 3 package NDCs
    and 1 product NDC, and package_ndc is populated on 100 of 100.

    Live: metformin now answers SITAGLIPTIN + METFORMIN HYDROCHLORIDE with
    UNIIs 786Z46389E and QFP0P1DV7Z and four package NDCs; aspirin's OTC
    label still answers with its `active_ingredient` prose. The two paths
    cover each other.
    """
    config = _config("FDA_get_manufacturer_name_NDC_number_by_drug_name")
    fields = config["fields"]["return_fields"]
    for field in (
        "openfda.substance_name",
        "openfda.unii",
        "openfda.package_ndc",
    ):
        assert field in fields, field
    # The OTC-only section is kept, not replaced.
    assert "active_ingredient" in fields


def test_a_parent_term_keeps_the_codes_its_record_carried():
    """One request per parent, already paid for.

    `DiseaseOntology_get_parents` fetches each parent's whole term record to
    read its name and definition, then returned the name, the definition and
    the grandparents. The rest of that record went in the bin -- including
    `xrefs`, which for DOID:9351 (diabetes mellitus, the parent of type 2
    diabetes) are ICD10CM:E08-E13, ICD9CM:250, MESH:D003920, NCI:C2985 and
    SNOMEDCT_US_2025_09_01:267467004.

    Those codes are how a caller carries a DO hierarchy into its own
    vocabulary, and the sibling `DiseaseOntology_get_term` can fetch them
    only by repeating a request this handler has already made. Synonyms come
    back for the same reason: a parent a caller's data calls something else
    is a parent it cannot match.
    """
    source = _source("disease_ontology_tool.py")
    assert '"cross_references": self._validated_list(' in source
    assert '"grandparents": grandparents' in source
    # The term handler and the parents handler now both report xrefs.
    assert source.count('_validated_list(data, "xrefs")') == 1
    schema = _config("DiseaseOntology_get_parents")["return_schema"]
    rows = (schema.get("oneOf") or [schema])[0]["properties"]["parents"][
        "items"
    ]["properties"]
    assert "ICD10CM" in rows["cross_references"]["description"]


def test_a_marker_species_says_that_it_is_one():
    """GMrepo's point is which microbes track a phenotype.

    `GMrepo_search_species` returned the taxon id, the name, the sample
    counts and the phenotype count, and dropped `ismarker` -- the flag that
    says GMrepo treats the species as a phenotype marker. All six
    Bacteroides hits for the live query are markers and the answer did not
    say so.

    `dblinks` went with it, and it needed handling rather than copying:
    GMrepo answers it as a JSON *string*, "[]" when empty, otherwise records
    like {"dbtype": "MVP", "anno": "assoc w/ 2 phage clusters", "url":
    ...}. 25 of 50 microbes sampled carry at least one. Passed through raw
    the string is unusable, so it is parsed, and a string that will not
    parse is reported under `raw` instead of dropped.
    """
    source = _source("gmrepo_tool.py")
    assert "def _dblinks" in source
    assert 'sp.get("ismarker")' in source
    assert '"raw": value' in source
    assert "_dblinks(sp)" in source
    schema = _config("GMrepo_search_species")["return_schema"]
    rows = (schema.get("oneOf") or [schema])[0]["items"]["properties"]
    assert "phenotype marker" in rows["is_marker"]["description"]
    assert "dbtype" in rows["database_links"]["items"]["properties"]


def test_a_trial_search_says_which_trials_reported_results():
    """Two of five metformin trials had posted results. The rows said
    nothing.

    `ClinicalTrials_search_studies`, `_by_intervention` and `_by_sponsor`
    share one row builder, and it read `protocolSection` only -- what each
    trial set out to do. The same search reply carries `hasResults` and, for
    the trials that have one, the whole `resultsSection`: on page one of a
    metformin search NCT02179788 comes back with 13 other adverse events and
    NCT00899470 with 17 outcome measure results and 17 adverse events. Every
    row reported `has_results: None`.

    The module already had `_results_summary` for this -- written for the
    per-study handler, which says in its own comment that what belongs in a
    row is "the fact that they exist, how much is in each, and which tool
    returns it". The search path never called it. One reader now serves both
    paths, so the counts and the tool names travel with every row and the
    hundreds of result rows stay in the tools that return them.
    """
    source = _source("ctg_tool.py")
    assert "def _results_summary" in source
    # One reader, called by the per-study handler and by the search row.
    assert source.count("_results_summary(") == 3
    assert "**_results_summary(s)," in source
    schema = _config("ClinicalTrials_search_by_intervention")["return_schema"]
    rows = (schema.get("oneOf") or [schema])[0]["properties"]["studies"][
        "items"
    ]["properties"]
    assert "hasResults" in rows["has_results"]["description"]
    assert "serious_adverse_events" in rows["results_summary"]["properties"]


def test_an_evidence_count_of_zero_was_a_misread_key():
    """154 of 264 features carry evidence; the count said 0 for all of them.

    `EBIProteins_get_proteins_by_genomic_loc` reported `evidence_count` from
    `feature.get("evidences")`. That endpoint answers `evidence`, singular --
    `/proteins/api/features` is the one that answers the plural, and
    measured live the two do not overlap: 154 of 264 features at 17:7676154
    carry `evidence` and none carries `evidences`, while 239 of P04637's
    1520 `/features` annotations carry `evidences` and none carries
    `evidence`.

    So the count was structurally zero. That is worse than a missing field:
    zero evidence reads as an unsupported annotation rather than as a
    question nobody asked. TP53's VAR_005856 has four ECO:0000269 records
    naming PubMed 1999338, 16131611 and 14702039, and those are returned now
    rather than counted.

    `nucleotide_id` came back with it -- CM000679.2 for chromosome 17, the
    sequence the coordinates are on. The sibling handler in this same module
    had always reported it.
    """
    source = _source("ebi_proteins_coordinates_tool.py")
    assert 'feature.get("evidence") or feature.get("evidences")' in source
    assert '"evidence": _evidence(feature)' in source
    assert source.count('"nucleotide_id": loc.get("nucleotideId")') == 1
    schema = _config("EBIProteins_get_proteins_by_genomic_loc")["return_schema"]
    proteins = (schema.get("oneOf") or [schema])[0]["properties"]["proteins"]
    props = proteins["items"]["properties"]
    assert "CM000679.2" in props["nucleotide_id"]["description"]
    evidence = props["features"]["items"]["properties"]["evidence"]
    assert "ECO:0000269" in json.dumps(evidence)


def test_round_forty_sevens_uniref_fix_reaches_the_search_too():
    """The fix went to the lookup and the search kept its old row.

    Round forty-seven gave `UniRef_get_cluster` the 253 members it was
    dropping. `UniRef_search_clusters`, in the same module, was not looked
    at, and the next shard of the audit found it: the search reply carries
    `members`, `goTerms` and `commonTaxon.taxonId`, and the row returned
    four `representative_*` fields and the common taxon's bare name.

    Two of those are now fixed here and one is deliberately not:

    * `go_terms` -- a cluster's GO annotations are the functional summary of
      the group. Both endpoints answer them and NEITHER handler read them,
      so no UniRef tool returned them anywhere; UniRef90_A5H1J3 is
      GO:0003677. The lookup gets them too, which round forty-seven missed.
    * `common_taxon_id` -- Amniota is 32524, and a name cannot be joined.
    * the members themselves stay out of the search row. `member_count` is
      there and `UniRef_get_cluster` now returns the records, so the row
      names that tool under `members_from` instead of repeating 200 member
      records per hit.
    """
    source = _source("uniref_tool.py")
    assert "def _go_terms" in source
    # Both handlers read them: the lookup and the search.
    assert source.count("_go_terms(") == 3
    assert 'common_taxon.get("taxonId")' in source
    assert '"members_from": "UniRef_get_cluster"' in source
    search = _config("UniRef_search_clusters")["return_schema"]
    rows = (search.get("oneOf") or [search])[0]["items"]["properties"]
    assert "32524" in rows["common_taxon_id"]["description"]
    assert "go_id" in rows["go_terms"]["items"]["properties"]


def test_an_entry_with_three_gene_names_reports_three():
    """P0DN86 is CGB3, CGB5 and CGB8. Both handlers said CGB3.

    `DisProt_search` and `DisProt_get_entry` each built their gene field as
    `genes[0].get("name", {}).get("value", "")` -- the first of however many,
    with no count and no list. A caller searching DisProt for CGB8 was
    answered with an entry labelled CGB3 and no way to see that CGB8 was one
    of its names.

    `gene` keeps its old meaning as the first name, so nothing that read it
    changes; `gene_names` and `gene_count` are new. This was found by
    grepping the module for `[0]` after round forty-seven had edited it --
    the same sweep that should have caught it the first time.

    GxA's experiment list had a single-field version of the same gap:
    `kingdom` is populated on all 4562 experiments (3481 animals, 1026
    plants, 54 fungi, 1 protist) and only the species name was returned, so
    "are there plant experiments" was a question about rows the caller could
    not see.
    """
    source = _source("disprot_tool.py")
    assert "def _gene_names" in source
    # Neither handler indexes the list any more.
    assert 'genes[0].get("name"' not in source
    # The two call sites, not the def line, which contains the same text.
    assert source.count("gene_names = _gene_names(genes)") == 2
    schema = _config("DisProt_search")["return_schema"]
    rows = (schema.get("oneOf") or [schema])[0]["items"]["properties"]
    assert "CGB8" in rows["gene_names"]["description"]
    gxa = _source("gxa_tool.py")
    assert 'exp.get("kingdom")' in gxa
    listing = _config("GxA_list_experiments")["return_schema"]
    exps = (listing.get("oneOf") or [listing])[0]["properties"]["experiments"]
    assert "4562" in exps["items"]["properties"]["kingdom"]["description"]


def test_an_annotation_says_where_in_the_paper_it_was_found():
    """"polysaccharides" -- in the argument, or in a supplementary .doc?

    Europe PMC answers `section`, `provider`, `frequency`, `fileName` and a
    resolvable `id` for every annotation, and those change what the
    annotation means. On MED:24295277 the chemical "polysaccharides" was
    found 4 times by Biostudies in `1476-069X-12-103-S1.doc` -- a
    supplementary Word document, not the article's text. A caller asking
    which chemicals a paper is about cannot weigh that without being told.

    Two handlers read this block and each dropped a different part: the
    per-article one kept section and provider and lost the id, and the batch
    one returned `exact`, `type` and `tags` alone. There is now one reader
    and both call it.
    """
    source = _source("europepmc_annotations_tool.py")
    assert "def _annotation_row" in source
    assert 'ann.get("frequency")' in source
    assert 'ann.get("fileName")' in source
    # One reader, called by the per-article handler and the batch handler.
    assert source.count("_annotation_row(ann) for ann in page") == 2
    for tool in (
        "EuroPMCAnnot_get_article_annotations",
        "EuroPMCAnnot_get_annotations_by_type",
    ):
        schema = json.dumps(_config(tool)["return_schema"])
        assert "Supplementary material" in schema, tool


def test_a_source_list_says_when_each_source_changed():
    """25 sources, 25 nulls, from one wrong key.

    `UniChem_list_sources` built `last_updated` from
    `s.get("lastUpdated", None)`. UniChem sends `srcLastUpdated`; there is no
    `lastUpdated` on the record. So the field was null for all 25 sources --
    not "this source has no date" but "nobody checked". It now reads
    2026-11-07 00:49:26 for SureChEMBL, with `last_checked` beside it, which
    is the different fact of when UniChem last found the source reachable.

    The two URLs went with it. `base_id_url` plus a compound id is the
    record's page (https://www.surechembl.org/chemical/ + id) and
    `source_url` is the source's home page. A tool whose whole job is to
    list the sources returned neither, so nothing it listed could be linked
    to.

    The compound-search handler in the same module reads `shortName`,
    `longName` and `url` from its own payload and returned nulls in testing;
    that endpoint is answering HTTP 500 upstream, so it is left alone rather
    than changed on a guess.
    """
    source = _source("unichem_tool.py")
    assert 's.get("srcLastUpdated")' in source
    assert 's.get("lastUpdated"' not in source
    assert 's.get("baseIdUrl")' in source
    assert 's.get("srcUrl")' in source
    rows = _config("UniChem_list_sources")["return_schema"]
    props = (rows.get("oneOf") or [rows])[0]["properties"]["sources"]["items"][
        "properties"
    ]
    assert "does not send" in props["last_updated"]["description"]
    assert "surechembl" in props["base_id_url"]["description"]


def test_a_signature_search_can_reach_the_signature():
    """It described files and gave no way to get one.

    `LINCS_search_signatures` returned a signature's annotations -- drug,
    cell line, dose, time point, tissue -- and dropped every field that
    leads to the data. SigCom LINCS answers a resolvable `persistent_id` for
    each signature
    (https://lincs-dcic.s3.amazonaws.com/LINCS-sigs-2021/cd/cp/L1000_LINCS_DCIC_CPC006_TYKNU_6H_F09_dexamethasone_10uM.tsv),
    the file name, its size and both checksums. It also answers `cmap_id`
    (CPC006_TYKNU_6H:BRD-A35108200-001-04-7:10), which is how a signature
    joins to the rest of the LINCS ecosystem.

    So the tool answered "which signatures exist for dexamethasone" and left
    the differential expression -- the thing a signature IS -- unreachable
    from its own reply. The file now comes with its checksum, because a
    caller fetching 345,287 bytes from S3 should be able to tell whether it
    arrived intact.
    """
    source = _source("lincs_tool.py")
    assert "def _signature_file" in source
    assert 'meta.get("persistent_id")' in source
    assert 'meta.get("sha256")' in source
    assert 'meta.get("cmap_id")' in source
    assert "_signature_file(meta)" in source
    schema = _config("LINCS_search_signatures")["return_schema"]
    rows = (schema.get("oneOf") or [schema])[0]["items"]["properties"]
    assert "sha256" in rows["data_file"]["properties"]
    assert "CPC006_TYKNU_6H" in rows["cmap_id"]["description"]


def test_a_translated_label_says_whether_hpo_stands_behind_it():
    """HP:0002069 is OFFICIAL in Japanese and CANDIDATE in Spanish and German.

    A CANDIDATE translation is a proposal, not a name the ontology has
    adopted, so a clinician matching a non-English record needs to know
    which it is -- and the status is a quarter of a four-key record. The
    term handler returned `language` and `name` only; the hierarchy handler
    returned no translations at all, although `translations` is one of the
    four keys its endpoint answers. One reader now serves both, so neither
    can drift from the other.
    """
    source = _source("hpo_tool.py")
    assert source.count("_translations(data)") == 1, (
        "HPO_get_term should build its translations through the shared reader"
    )
    assert source.count("_translations(term)") == 1, (
        "HPO_get_term_hierarchy returned no translations at all; its rows "
        "should use the same reader as HPO_get_term"
    )
    assert 'item.get("definition")' in source, (
        "HPO publishes a translated definition beside the translated name"
    )


def test_a_membrane_placement_says_whether_it_was_checked_against_experiment():
    """OPM reports thickness, tilt and transfer energy -- all computed.

    `verification` is where OPM says whether those numbers were confirmed:
    for 1m0l, "Results are consistent with solid state NMR studies of
    bacteriorhodopsin (Kamihira et al. 2005)". Sparse -- 16 of 395 records
    sampled across five queries -- but it is the only statement the database
    makes about the standing of the geometry the tool exists to report, so
    its absence is not the same as its being empty.

    `tau` is deliberately not read: 0 of those same 395 records populate it.
    """
    source = _source("membrane_topology_tool.py")
    assert 'o.get("verification")' in source
    assert 'o.get("tau")' not in source, (
        "tau is empty on every OPM record sampled; reading a key the API "
        "never fills declares a field that can only ever be null"
    )


def test_a_structure_search_can_reach_the_opm_record():
    """The detail endpoint answers 200 for a PDB id -- with the wrong protein.

    /primary_structures/1uaz returns id 1, pdbid 1qjp, an unrelated outer
    membrane porin, because the path segment is coerced to an integer. A
    caller holding only the PDB id the search returned would have taken that
    record as the answer. The numeric id is the only safe way in, and the
    search dropped it along with the family and species ids that reach the
    classification and taxonomy behind each row.
    """
    source = _source("membrane_topology_tool.py")
    for key in ('"opm_id": o.get("id")', '"family_id": o.get("family_id")',
                '"species_id": o.get("species_id")'):
        assert key in source, f"OPM search should return {key}"
    assert "opm.phar.umich.edu/proteins/" in source, (
        "the row should carry the OPM page it describes"
    )
    schema = json.dumps(_config("OPM_search_structures").get("return_schema"))
    assert '"url"' in schema, "the OPM page URL must be declared"


def test_a_payment_carries_the_key_that_joins_it_across_years():
    """A recipient name is ambiguous and a teaching hospital has no NPI.

    CMS publishes `covered_recipient_profile_id` for exactly this: it is the
    id the Open Payments site uses in its own URLs and the only stable way
    to follow one recipient across program years. The wrapper returned the
    name and the NPI and dropped it.

    The recipient's street address is in the same record and is deliberately
    not returned: it is published, but it is not what the question needs.
    """
    source = _source("cms_open_payments_tool.py")
    assert 'row.get("covered_recipient_profile_id")' in source
    assert 'row.get("change_type")' in source, (
        "whether CMS changed or merely republished the record is how a "
        "caller knows a figure moved between publications"
    )


def test_a_dataset_of_gene_sets_can_reach_a_gene_set():
    """CTD Gene-Disease Associations holds 5218 gene sets in Harmonizome.

    The wrapper named a page of them and returned no pointer, and nothing
    in the catalogue takes a gene-set name -- there is no
    Harmonizome_get_gene_set. So every one of those 5218 names was a dead
    end. The href the API ships beside each name resolves to the genes with
    their threshold and standardized values, which is the thing a gene set
    is.

    The name is still trimmed at the slash on purpose: Harmonizome
    qualifies each name with its dataset, and the dataset is the one asked
    for. The href carries the unabbreviated form.
    """
    source = _source("harmonizome_tool.py")
    assert 'gs.get("href")' in source
    assert "HARMONIZOME_SITE" in source, (
        "the href is a bare path; a resolvable URL should travel with it"
    )
    assert 'resource.get("name")' in source, (
        "a Harmonizome dataset is a processed view of another database, and "
        "the tool reported the processing without the origin"
    )


def test_a_polygenic_score_says_what_it_was_trained_and_discovered_in():
    """samples_training and samples_variants are different populations.

    samples_training is where the weights were fitted; samples_variants is
    the GWAS the variants were discovered in. A score's transferability
    depends on both, the module docstring promises both, and only the first
    reached any handler. PGS000018 carries seven discovery samples, from
    East Asian (11,323) to Hispanic or Latin American (4,095), each with
    its GWAS Catalog accession.
    """
    source = _source("pgs_catalog_tool.py")
    assert 'body.get("samples_variants")' in source
    assert 'v.get("source_GWAS_catalog")' in source, (
        "the discovery GWAS accession is what joins the score to GWAS Catalog"
    )
    assert 'body.get("license")' in source, (
        "the tool returns a scoring-file URL; the licence governing its "
        "reuse travelled in the same record and was dropped"
    )
    assert 'body.get("method_params")' in source, (
        "method_name without method_params is a method with no thresholds"
    )


def test_a_topology_tool_says_where_the_segments_are():
    """num_tm_segments answered "16" to the question of which residues cross.

    PDBTM assigns every residue to one of eight regions and ships the legend
    that names them; the wrapper returned the count and neither. The
    per-residue data collapses into labelled ranges, and on 2por every chain
    yields exactly 16 transmembrane runs against a reported num_tm of 16 --
    and on 1prc, 5, 5 and 1 for the L, M and H subunits. That agreement is
    the check that the collapse is faithful rather than merely plausible.
    """
    source = _source("pdbtm_tool.py")
    assert "_topology_segments(chain, site_labels)" in source
    assert 'res.get("aa_type")' in source, (
        "a residue range should say which residues it covers"
    )
    assert 'site.get("site_id")' in source and 'site.get("label")' in source, (
        "the region legend turns a site id into 'Transmembrane Beta strand'"
    )
    assert 'payload.get("model_coordinates_url")' in source, (
        "a structure database that returns no way to fetch the structure "
        "is a dead end"
    )
    schema = json.dumps(_config("PDBTM_get_topology").get("return_schema"))
    assert '"topology_segments_truncated"' in schema, (
        "the 200-segment cap must be disclosed"
    )


def test_a_disease_term_carries_its_mappings_and_its_place_in_the_ontology():
    """Everything missing sat at the top level of the response, beside doTerm.

    The handler read doTerm and category and stopped, so DOID:162 came back
    as a name, a definition and some synonyms -- with no mapping to
    MESH:D009369, UMLS_CUI:C0006826, ICD9CM:199, ICD10CM:C80.1 or SNOMEDCT,
    no link to where RGD, MGI, ZFIN, FlyBase, WormBase and SGD keep their
    annotations for it, and no parents or children. All three were in the
    payload it had already parsed.

    SNOMEDCT arrives with a curie and no url while the others carry both,
    so the url is optional in a cross-reference and the curie is not.
    """
    source = _source("alliance_genome_tool.py")
    assert 'data.get("crossReferenceLinkUrls")' in source
    assert 'data.get("parents")' in source and 'data.get("children")' in source
    assert 'row.get("referencedCurie")' in source, (
        "the curie is the required half of a cross-reference"
    )


def test_a_neuron_specimen_carries_the_physiology_the_tool_advertises():
    """The description promises electrophysiology, donor and structure data.

    It returned four electrophysiology features and dropped seven, among
    them resting membrane potential and rheobase -- the two most basic
    intrinsic properties a neuron has. It returned the structure and not
    the layer inside it, though layer 3 and layer 5 pyramidal cells are
    different cell types. And it returned the donor's species, sex and age
    but not the donor's identity, so three specimens from one brain
    (H15.06.016) were indistinguishable from three brains.

    tag__dendrite_type is the one that changes an answer: of three
    specimens from that donor, two are spiny and one aspiny, which is the
    standard proxy for excitatory versus inhibitory.
    """
    source = _source("allen_cell_types_tool.py")
    for key in ('r.get("ef__vrest")', 'r.get("ef__threshold_i_long_square")',
                'r.get("structure__layer")', 'r.get("tag__dendrite_type")',
                'r.get("donor__id")'):
        assert key in source, f"the specimen row should carry {key}"
    schema = json.dumps(_config("AllenCellTypes_search_specimens").get("return_schema"))
    assert "tissue block" in schema, (
        "the soma coordinate is per cell for mouse and coarser for human; "
        "the schema must say so rather than imply a cell-level position"
    )


def test_a_cross_reference_tool_says_what_the_cross_reference_says():
    """RNAcentral returns MalaCards as one row among the cross-references.

    That row's payload is the list of diseases the microRNA is associated
    with: 364 of them for hsa-miR-21-5p, each with a resolvable card URL.
    The wrapper reported that a MalaCards cross-reference existed and
    dropped what it said, which for a tool whose entire subject is
    cross-references is the answer rather than a detail of it.

    Three keys were measured and deliberately left out, because 0 of 80
    rows across four microRNAs populate any of them:
    refseq_mirna_mature_products, refseq_mirna_precursor and hgnc_id. What
    looked at first like sibling drift against the mirbase_* keys was not
    drift at all -- those measured 0/80 on the same sample.
    """
    source = _source("mirna_tool.py")
    assert 'acc.get("malacards_diseases")' in source
    assert "DISEASES_PER_XREF" in source, "the per-row cap must be a named constant"
    assert '"diseases_truncated"' in source, "the cap must be disclosed"
    for never_filled in (
        'xref.get("refseq_mirna_mature_products")',
        'xref.get("refseq_mirna_precursor")',
        'acc.get("hgnc_id")',
    ):
        assert never_filled not in source, (
            f"{never_filled} is empty on all 80 rows sampled; reading it "
            "would declare a field that can only ever be null"
        )


def test_a_citations_field_is_not_a_count():
    """RNAcentral's `citations` key holds a URL.

    I named the field citation_count first; the live response disagreed, so
    it is citations_url. A schema that promises a number and returns
    "https://rnacentral.org/api/v1/accession/.../citations?format=json" is
    a worse failure than the omission it replaced.
    """
    source = _source("mirna_tool.py")
    assert '"citations_url": acc.get("citations")' in source
    assert '"citation_count"' not in source
    schema = json.dumps(_config("miRBase_get_mirna_xrefs").get("return_schema"))
    assert '"citations_url"' in schema and '"citation_count"' not in schema


def test_a_classification_carries_the_identifiers_that_make_it_citable():
    """`_name()` collapsed every ChemOnt node to its name string.

    ClassyFire ships each node as {name, description, chemont_id, url}, so
    the tool said aspirin's class was "Benzene and substituted derivatives"
    and discarded CHEMONTID:0002279 -- a citable ontology term turned into
    prose that nothing downstream can join on, and that two tools cannot
    agree they mean the same of.

    The plain name fields are deliberately unchanged, so existing callers
    keep working; the ids arrive alongside them. Aspirin's five levels run
    CHEMONTID:0000000 to CHEMONTID:0004577, and it has ten alternative
    parents -- phenol esters, benzoic acids, phenoxy compounds -- of which
    the caller previously saw none.
    """
    source = _source("classyfire_tool.py")
    assert 'node.get("chemont_id")' in source
    assert "def _name(" in source, (
        "the name-only helper must stay: the string fields it feeds are "
        "what existing callers read"
    )
    assert 'rec.get("alternative_parents")' in source
    assert 'rec.get("predicted_chebi_terms")' in source, (
        "ChemOnt is not a vocabulary most callers hold; the predicted ChEBI "
        "terms are how the classification reaches one they do"
    )
    schema = json.dumps(_config("ClassyFire_classify_by_inchikey").get("return_schema"))
    assert '"alternative_parent_count"' in schema, (
        "the 50-parent cap must be disclosed"
    )


def test_spliceai_reports_a_string_delta_score_as_the_number_it_is():
    """Every variant was reported benign, because the scores are strings.

    SpliceAI sends its deltas as `"DS_AL": "0.827"`. The maximum was
    computed with

        if val is not None and isinstance(val, (int, float)):

    which is False for every string, so the maximum never moved off its 0.0
    seed. Both SpliceAI tools answered `max_delta_score: 0.0,
    interpretation: "benign"` for chr8-140300616-T-G -- this tool's own
    test example -- whose DS_AL is 0.827, which the tool's own thresholds
    call high_pathogenicity. A variant triage tool that calls everything
    benign is worse than one that returns nothing.

    This is checked against the upstream shape rather than the network: the
    strings below are exactly what the API sends.
    """
    from tooluniverse.spliceai_tool import SpliceAITool

    tool = SpliceAITool({"fields": {"operation": "get_max_delta"}})
    upstream_shape = [
        {
            "DS_AG": "0.045", "DS_AL": "0.827",
            "DS_DG": "0.000", "DS_DL": "0.618",
            "DP_AG": -32, "DP_AL": -2, "DP_DG": 66, "DP_DL": -147,
            "g_name": "TRAPPC9", "t_id": "ENST00000438773.4",
        }
    ]
    summary = tool._max_delta(upstream_shape)
    assert summary["max_delta_score"] == 0.827, (
        "a string delta must be parsed, not skipped as a non-number"
    )
    assert tool._interpret_score(summary["max_delta_score"]) == (
        "high_pathogenicity"
    )
    assert summary["max_delta_effect"] == "acceptor_loss", (
        "0.827 by acceptor loss is a different consequence from 0.827 by "
        "donor gain, and the score alone does not say which"
    )
    assert summary["max_delta_offset"] == -2
    assert summary["delta_by_effect"]["donor_loss"] == 0.618


def test_spliceai_does_not_report_an_absent_prediction_as_benign():
    """No parseable score is `unknown`, not 0.0.

    The old seed of 0.0 meant "nothing came back" and "SpliceAI scored this
    at zero" produced the same answer, and that answer was benign. A
    genuinely all-zero response still reads benign, which is correct; an
    empty or unparseable one now reads unknown.
    """
    from tooluniverse.spliceai_tool import SpliceAITool

    tool = SpliceAITool({"fields": {"operation": "get_max_delta"}})
    for nothing in ([], [{"DS_AG": "n/a"}], [{}], ["not a dict"]):
        summary = tool._max_delta(nothing)
        assert summary["max_delta_score"] is None, nothing
        assert tool._interpret_score(summary["max_delta_score"]) == "unknown"

    real_zero = tool._max_delta(
        [{"DS_AG": "0.000", "DS_AL": "0.000", "DS_DG": "0.000", "DS_DL": "0.000"}]
    )
    assert real_zero["max_delta_score"] == 0.0
    assert tool._interpret_score(real_zero["max_delta_score"]) == "benign"
    # isinstance(True, int) is True in Python, so a bool must not pass for a
    # score: it would be reported as 1.0, the top of the scale.
    assert tool._as_float(True) is None


def test_a_stability_call_needs_a_number_behind_it():
    """"destabilizing" was the else branch of a two-way if.

        "stabilizing" if isinstance(ddg, (int, float)) and ddg > 0
        else "destabilizing"

    Both DynaMut2 handlers used that, so a prediction DynaMut2 did not
    return, or returned unparseably, came back as a confident
    "destabilizing". The float() coercion above those call sites handles the
    ordinary string case, which makes this narrower than the SpliceAI
    defect it resembles -- but a directional stability call with no number
    behind it is still an answer the data does not support.

    How often DynaMut2 leaves `prediction` unparseable is not measured: it
    submits jobs by ticket and polls for them, so a population estimate
    would take hours of queueing. The fix is correct at any frequency.

    A ddG of exactly 0 still reads destabilizing, as it always has; only
    the no-number case changed.
    """
    from tooluniverse.dynamut2_tool import _effect

    assert _effect(1.5) == "stabilizing"
    assert _effect(-1.5) == "destabilizing"
    assert _effect(0.0) == "destabilizing"
    assert _effect("1.5") == "stabilizing", (
        "the helper coerces rather than trusting its callers to have done it"
    )
    for no_number in (None, "", "n/a", [1.0], {}):
        assert _effect(no_number) == "unknown", no_number
    # isinstance(True, int) is True and True > 0, so a bool would read as a
    # stabilizing prediction.
    assert _effect(True) == "unknown"

    source = _source("dynamut2_tool.py")
    # Anchored on the assignment, not on "_effect(ddg)": that substring is
    # also in `def _effect(ddg) -> str:`, so the bare form counts 3 and the
    # guard fails against the fixed tree. Same trap as _gene_names(genes).
    assert source.count("effect = _effect(ddg)") == 2, (
        "both handlers must go through the one reader"
    )
    schema = json.dumps(_config("DynaMut2_predict_stability").get("return_schema"))
    assert "unknown" in schema, (
        "the schema promised only stabilizing or destabilizing; there is a "
        "third value now"
    )


def test_a_schema_does_not_declare_a_field_the_api_never_sends():
    """umls_get_concept_details declared `definition`; UMLS sends `definitions`.

    The singular form is not a key the API has, so the schema promised a
    field that could never be populated while omitting the fourteen result
    keys the API does send -- among them semanticTypes, which is how a
    caller tells a disease concept from a drug one, and suppressible, which
    says whether UMLS still stands behind the concept at all. Same shape as
    UniChem's `lastUpdated` against the `srcLastUpdated` it actually sends,
    reached from the schema side instead of the wrapper side.
    """
    schema = json.dumps(_config("umls_get_concept_details").get("return_schema"))
    assert '"definitions"' in schema
    assert '"definition"' not in schema.replace('"definitions"', ""), (
        "the singular field is not a key UMLS sends"
    )
    for real in ('"semanticTypes"', '"suppressible"', '"atomCount"'):
        assert real in schema, f"UMLS returns {real} and the schema omitted it"


def test_a_geocode_result_declares_its_licence_and_its_osm_key():
    """Nominatim's payload carries the attribution ODbL requires.

    The result says 'Data (c) OpenStreetMap contributors, ODbL 1.0' and the
    schema did not mention it, so an agent deciding what the tool returns
    had no way to know an attribution obligation came with the answer. The
    same row carries osm_type and osm_id, which identify the object in
    OpenStreetMap; place_id, which the schema did declare, is a
    Nominatim-internal number that changes between imports.
    """
    for tool in ("Nominatim_geocode", "Nominatim_reverse_geocode"):
        schema = json.dumps(_config(tool).get("return_schema"))
        assert '"licence"' in schema, f"{tool} returns the licence undeclared"
        assert '"osm_type"' in schema and '"osm_id"' in schema, (
            f"{tool} returns the OSM key undeclared"
        )
        assert "ODbL" in schema, (
            "the declaration should name the licence, not just the field"
        )


def test_a_literature_search_declares_whether_a_work_was_retracted():
    """openalex_search_works declared four of the fifty-three keys it returns.

    `id`, `title`, `doi`, `publication_year` were declared;
    `is_retracted` was not. A literature result whose schema does not
    mention retraction can be read, cited and built on in good faith after
    the paper has been withdrawn -- and an agent choosing tools from the
    schema would not know the tool can answer the question at all.

    The same record carried `authorships` with each author's affiliation
    and ORCID, `ids` with the PMID and PMCID that turn an OpenAlex hit into
    a PubMed lookup, `best_oa_location` with a readable copy, `mesh`,
    `biblio` (the volume, issue and pages a citation needs and the DOI does
    not give), and `referenced_works`. The wrapper returns the upstream
    payload whole, so none of this was ever dropped: it was returned and
    undeclared, which the audit treats as the second half of the same
    defect.

    `additionalProperties: true` was already on the results item and did
    not help: a boolean says the level is open without saying what is in
    it, so it declares nothing a reader can act on.
    """
    schema = json.dumps(_config("openalex_search_works").get("return_schema"))
    for field in ('"is_retracted"', '"is_paratext"', '"authorships"', '"ids"',
                  '"best_oa_location"', '"mesh"', '"biblio"',
                  '"referenced_works"', '"fwci"'):
        assert field in schema, f"openalex_search_works returns {field} undeclared"
    assert "ORCID" in schema, (
        "the authorship declaration should say the author carries an ORCID"
    )
    assert "inverted index" in schema, (
        "OpenAlex ships no plain-text abstract; a caller has to rebuild it "
        "from abstract_inverted_index, and the schema should say so"
    )


def test_a_search_tool_declares_what_the_upstream_says_about_the_request():
    """OpenAlex answers every keyless request with a budget warning.

    `meta.notice` says the caller is sharing one free $0.10 per day across
    everyone on the same network IP, and how to get a key; `meta.cost_usd`
    says what the request drew against it. That is the difference between
    a tool that mysteriously starts failing under load and one whose answer
    said why, and neither field was declared.
    """
    schema = json.dumps(_config("openalex_search_works").get("return_schema"))
    assert '"notice"' in schema and '"cost_usd"' in schema
    assert "0.10" in schema or "budget" in schema, (
        "the notice declaration should say what the notice is about"
    )


def test_a_dataset_record_says_whether_the_data_can_be_had():
    """Figshare_get_article declared 13 of the 50 keys it returns.

    The undeclared ones included every field that says whether the dataset
    is actually available: is_embargoed with its date and reason,
    is_confidential, download_disabled, and is_metadata_record -- which is
    true when there is no data behind the record at all, however complete
    the description looks. A tool that returns a Figshare article without
    those is describing a dataset the caller may not be able to have, and
    saying nothing about it.

    files[] was declared as a bare array, so its item shape was undeclared
    too, and that item carries download_url with both computed_md5 and
    supplied_md5. That is the same triad as the LINCS round -- can I fetch
    the bytes, can I verify them, can I join this to my own data -- except
    here the wrapper was already returning all three and the schema hid
    them. Figshare returns two MD5s on purpose: the depositor's and its own,
    and a mismatch is a provenance problem, so both travel.

    resource_doi and resource_title are the join from a dataset to the paper
    it belongs to; for the test article, 10.3389/fmicb.2021.669230.
    """
    schema = json.dumps(_config("Figshare_get_article").get("return_schema"))
    for availability in ('"is_embargoed"', '"embargo_date"',
                         '"download_disabled"', '"is_metadata_record"',
                         '"is_confidential"'):
        assert availability in schema, f"{availability} undeclared"
    for fetchable in ('"download_url"', '"computed_md5"', '"supplied_md5"'):
        assert fetchable in schema, f"files[] item is missing {fetchable}"
    assert '"resource_doi"' in schema and '"orcid_id"' in schema
    assert "metadata only" in schema, (
        "is_metadata_record needs to say what it means: there is no data "
        "behind the record"
    )


def test_a_pathway_record_says_whether_it_was_curated_or_inferred():
    """Reactome_get_interactor declared 25 keys and omitted fifteen.

    Two of them decide how much the record is worth. `isInferred` says
    whether the event was curated for this species or computationally
    projected from another, and `reviewStatus` is Reactome's own confidence
    in the curation - R-HSA-73817 comes back as "five stars". A pathway
    returned without either reads as settled fact regardless of which it is.

    Also undeclared: `summation`, which is the curated prose describing the
    event; `literatureReference`, the papers the curation rests on;
    `goBiologicalProcess`, the GO term it maps to; `species` and
    `compartment`; and `orthologousEvent`, the same event in other species.
    """
    schema = json.dumps(_config("Reactome_get_interactor").get("return_schema"))
    for field in ('"isInferred"', '"reviewStatus"', '"summation"',
                  '"literatureReference"', '"goBiologicalProcess"',
                  '"orthologousEvent"'):
        assert field in schema, f"Reactome returns {field} undeclared"
    assert "five stars" in schema, (
        "reviewStatus is a rating; the declaration should show what one "
        "looks like"
    )


def test_a_taxon_suggestion_carries_the_keys_that_resolve_it():
    """GBIF returned the classification as names with none of the keys.

    kingdom, phylum, class, order, family and genus were declared;
    kingdomKey, phylumKey, classKey, orderKey, familyKey and genusKey were
    not, so the classification could be read and not followed. Nor was
    nubKey, which is the backbone taxon the name matched - and that is the
    one that matters, because `key` is the key of this name record and for a
    synonym the two differ.

    higherClassificationMap is keyed by backbone taxon key out of the data,
    so it is declared with additionalProperties and a value shape rather
    than a list of keys that only exist for this one query.
    """
    schema = json.dumps(_config("GBIF_suggest_species").get("return_schema"))
    assert '"nubKey"' in schema
    for rank in ("kingdomKey", "phylumKey", "classKey", "orderKey",
                 "familyKey", "genusKey"):
        assert f'"{rank}"' in schema, f"{rank} undeclared"
    # The field name was already declared as a bare object: the audit said
    # `[].higherClassificationMap.*`, meaning the level was named and its
    # contents were not. Asserting the name would pass against the unfixed
    # schema, so this asserts the value shape.
    assert "Taxon name for that key" in schema, (
        "higherClassificationMap was declared without a value shape"
    )
    assert "synonym" in schema, (
        "the nubKey declaration should say why it is not the same as key"
    )
