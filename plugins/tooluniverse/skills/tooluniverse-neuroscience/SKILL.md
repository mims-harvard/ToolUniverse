---

name: tooluniverse-neuroscience
description: "Neuroscience research workflows: neuroanatomy, neural circuits, neurotransmitter biology, neurological/psychiatric disease genetics, neural-protein function. Uses Allen Brain Atlas, WormBase (C. elegans connectome), UniProt for neural proteins, PubMed for primary literature. Use for brain-region biology, neural development, neurodegeneration mechanisms (Alzheimer's, Parkinson's, ALS), and synaptic-protein characterization."
---

# Neuroscience Research Skill

**KEY PRINCIPLES**: LOOK UP, DON'T GUESS — use PubMed/EuropePMC for neuroanatomy facts, WormBase for C. elegans connectome data, UniProt for neural protein properties. Verify claims with literature before answering. Use Python computation for quantitative neuroscience problems.

---

## LOOK UP, DON'T GUESS
When uncertain about any neuroscience fact — brain region function, neural circuit connectivity, ion channel properties, neurotransmitter receptor subtypes — SEARCH databases first. A PubMed-verified answer is always more reliable than reasoning from memory. This is especially critical for neuroanatomy, where structures have precise boundaries and connectivity patterns that are easy to confuse.

---

## 1. Computational Neuroscience Reasoning

### Rate-Based Models
- Firing rate of a neuron: r = f(I - theta), where I = total synaptic input, theta = threshold, f = transfer function (sigmoid, ReLU, or threshold-linear)
- Balanced excitation/inhibition: in cortical networks, excitatory and inhibitory inputs are large but nearly cancel, leaving a small net drive
- Population rate equations: tau * dr/dt = -r + f(W*r + I_ext), where W = connectivity matrix
- Steady-state analysis: set dr/dt = 0, solve r = f(W*r + I_ext) — use fixed-point iteration or Newton's method

### Integrate-and-Fire Neurons
- Membrane voltage dynamics: tau_m * dV/dt = -(V - V_rest) + R_m * I(t)
- When V reaches threshold V_th: emit spike, reset to V_reset, enter refractory period tau_ref
- Firing rate for constant input: r = 1 / (tau_ref + tau_m * ln((R_m*I - V_reset) / (R_m*I - V_th))) [valid when R_m*I > V_th]
- For sub-threshold input: neuron requires fluctuations (noise) to fire — noise-driven regime
- Key variants: LIF (leaky), EIF (exponential), AdEx (adaptive exponential), Izhikevich (2D with recovery variable)

### Synaptic Plasticity
- **STDP** (Spike-Timing-Dependent Plasticity):
  - Pre-before-post (positive dt): LTP (potentiation) — synapse strengthened
  - Post-before-pre (negative dt): LTD (depression) — synapse weakened
  - Window shape: typically exponential decay with tau_+ ~ 20ms (LTP) and tau_- ~ 20ms (LTD)
- **Hebbian learning**: "cells that fire together wire together" — correlation-based; unstable without normalization
- **BCM theory**: sliding threshold — low postsynaptic activity → LTD, high → LTP; threshold slides with average activity
- **Homeostatic plasticity**: synaptic scaling adjusts all synapses multiplicatively to maintain target firing rate

### Network Dynamics
- **Mean-field theory**: replace individual neurons with population-averaged firing rates; self-consistency equation r = f(J*r*sqrt(K) + I_ext) where K = number of connections
- **Balanced networks**: E/I balance emerges when sqrt(K)*J ~ O(1); firing rate ~ (mu - theta) / tau where mu = mean input, theta = threshold
- **Chaos transition**: in random networks, chaos onset at g_c = 1 (gain parameter); above g_c, autocorrelation decays, Lyapunov exponent > 0
- **Oscillations**: gamma (30-80 Hz) from E-I loops (PING model), theta (4-8 Hz) from slower inhibition or hippocampal circuits, alpha (8-12 Hz) from thalamo-cortical loops

### Quantitative Problem-Solving Strategy
1. Identify the model type (single neuron, network, plasticity rule)
2. Write down the governing equations with all parameters
3. **ALWAYS use Python** for multi-step calculations — do not attempt mental arithmetic
4. Check units: voltages in mV, currents in nA or pA, time constants in ms, rates in Hz
5. Sanity check: cortical firing rates are typically 1-20 Hz; tau_m ~ 10-20 ms; V_th ~ -50 mV

---

## 2. Neuroanatomy Reasoning

### CRITICAL: Look Up Neuroanatomy
Brain region functions, boundaries, and connectivity are precise anatomical facts. When asked about specific regions, nuclei, or tracts:
1. Search PubMed or EuropePMC with specific anatomical terms
2. For connectivity: search "[region A] projection [region B]" or "[region] afferents efferents"
3. For function: search "[region] lesion" or "[region] function review"

### Human Brain — Major Divisions
- **Cerebral cortex**: frontal (motor, executive), parietal (somatosensory, spatial), temporal (auditory, memory), occipital (visual)
- **Basal ganglia**: caudate + putamen (striatum) → GPi/SNr (output) → thalamus; direct pathway (facilitate movement) vs indirect pathway (suppress movement); dopamine from SNc modulates both
- **Cerebellum**: coordination, timing, motor learning; receives mossy fibers (pontine nuclei) and climbing fibers (inferior olive); Purkinje cells are sole output of cerebellar cortex
- **Brainstem**: midbrain (superior/inferior colliculi, substantia nigra, red nucleus), pons (pontine nuclei, respiratory centers), medulla (cardiovascular/respiratory centers, cranial nerve nuclei)
- **Thalamus**: relay station — every sensory modality (except olfaction) synapses here before cortex; also receives cortical feedback (corticothalamic loops)
- **Hippocampus**: declarative memory formation; trisynaptic circuit: EC → DG → CA3 → CA1 → EC; place cells, grid cells

### Model Organism Neuroanatomy
- **C. elegans**: 302 neurons, complete connectome mapped; use `WormBase_get_gene` for gene expression, neuron identity, connectivity data
- **Drosophila**: mushroom body (learning/memory), antennal lobe (olfaction), central complex (navigation); ~100,000 neurons; FlyWire connectome
- **Zebrafish**: transparent larvae for whole-brain imaging; Mauthner cells (escape response); use `Alliance_search_genes` for orthologs
- **Mouse**: Allen Brain Atlas for gene expression; use PubMed for circuit tracing studies (rabies virus, optogenetics)

### Reasoning Pattern for "Where in the Brain?" Questions
1. Identify the function asked about (motor, sensory, memory, emotion, language)
2. Map to candidate regions from general knowledge
3. VERIFY with PubMed search: "[function] brain region fMRI" or "[function] lesion study"
4. Check for lateralization (language → usually left hemisphere)
5. Distinguish cortical vs subcortical involvement

---

## 3. Clinical Neurology Reasoning

### Cranial Nerve Examination
- Map symptom → nerve → nucleus → lesion site:
  - CN I (olfactory): anosmia — cribriform plate fracture, frontal lobe lesion
  - CN II (optic): visual field defects — optic nerve, chiasm, tract, radiation, cortex
  - CN III (oculomotor): ptosis, "down and out" eye — midbrain, posterior communicating artery aneurysm
  - CN IV (trochlear): difficulty looking down-and-in — dorsal midbrain
  - CN V (trigeminal): facial sensation loss, jaw deviation — pons, Meckel's cave
  - CN VI (abducens): medial strabismus — pons (long intracranial course, vulnerable to raised ICP)
  - CN VII (facial): upper vs lower face weakness distinguishes UMN (forehead spared) vs LMN (all ipsilateral)
  - CN VIII (vestibulocochlear): hearing loss, vertigo — peripheral vs central distinction critical
  - CN IX-X (glossopharyngeal, vagus): dysphagia, uvula deviation
  - CN XI (accessory): SCM and trapezius weakness
  - CN XII (hypoglossal): tongue deviation toward lesion side

### Stroke Localization
- **Anterior circulation** (ICA, MCA, ACA): MCA → contralateral face/arm > leg weakness, aphasia (dominant), neglect (non-dominant); ACA → contralateral leg > arm weakness
- **Posterior circulation** (vertebrobasilar): brainstem signs (cranial nerve palsies + crossed signs), cerebellar ataxia, visual field defects
- **Cortical vs subcortical**: cortical → higher function deficits (aphasia, neglect, agnosia); subcortical (lacunar) → pure motor/sensory without cortical signs
- **Key rule**: crossed signs (ipsilateral face + contralateral body) = brainstem lesion

### Upper vs Lower Motor Neuron
| Feature | UMN Lesion | LMN Lesion |
|---------|-----------|-----------|
| Tone | Increased (spastic) | Decreased (flaccid) |
| Reflexes | Hyperreflexia, Babinski+ | Hyporeflexia/areflexia |
| Atrophy | Minimal (disuse) | Prominent, early |
| Fasciculations | Absent | Present |
| Distribution | Pyramidal pattern | Specific nerve/root |

### Neurodegenerative Disease Patterns
- **Alzheimer's**: amyloid plaques + tau tangles; hippocampus → entorhinal cortex → neocortex; episodic memory loss first
- **Parkinson's**: alpha-synuclein in substantia nigra pars compacta; dopamine depletion → bradykinesia, rigidity, resting tremor; search `UniProt_search` for SNCA, LRRK2, PARK7
- **ALS**: upper AND lower motor neuron signs; TDP-43 pathology; SOD1, C9orf72 genes
- **Huntington's**: CAG repeat expansion in HTT; caudate atrophy; chorea, psychiatric symptoms, cognitive decline

### Reasoning Pattern for Clinical Neuro Questions
1. Localize the lesion: what neurological structure explains ALL the findings?
2. Single lesion principle: prefer one lesion that explains everything over multiple lesions
3. Determine mechanism: vascular (sudden onset), inflammatory (subacute), degenerative (gradual), neoplastic (progressive with mass effect)
4. VERIFY with literature if uncertain about anatomy or presentation

---

## 4. Neurophysiology Reasoning

### Action Potential
- Resting potential ~ -70 mV (K+ equilibrium ≈ -90 mV, Na+ ≈ +60 mV, weighted by conductances)
- Nernst equation: E_ion = (RT/zF) * ln([ion]_out / [ion]_in) ≈ 61.5/z * log10([out]/[in]) mV at 37C
- Goldman equation for resting potential: accounts for relative permeabilities of Na+, K+, Cl-
- AP phases: depolarization (Na+ channels open) → overshoot → repolarization (K+ channels open, Na+ inactivate) → hyperpolarization (K+ channels slow to close)
- Refractory periods: absolute (no stimulus can fire) ~ 1 ms; relative (stronger stimulus needed) ~ 2-4 ms

### Synaptic Transmission
- Chemical synapse: AP → Ca2+ entry (N-type, P/Q-type channels) → vesicle fusion (SNARE complex) → neurotransmitter release → postsynaptic receptor binding
- Excitatory: glutamate → AMPA (fast, Na+/K+), NMDA (slow, Ca2+, voltage-dependent Mg2+ block)
- Inhibitory: GABA → GABA_A (fast, Cl-), GABA_B (slow, K+, G-protein coupled); glycine in spinal cord
- Neuromodulators: dopamine, serotonin, norepinephrine, acetylcholine — volume transmission, slower, alter circuit gain

---

## 5. Available Tools

| Tool | Use For | Key Parameters |
|------|---------|---------------|
| `PubMed_search_articles` | Neuroanatomy facts, clinical neurology, circuit studies | `query`, `limit` |
| `EuropePMC_search_articles` | Broader literature including preprints | `query`, `limit` |
| `WormBase_get_gene` | C. elegans neurons, connectome, gene expression | `query` |
| `DANDI_search_datasets`/`DANDI_get_dataset`/`DANDI_list_assets` | Published neurophysiology data (NWB format): spikes, LFP, imaging, behavior | `query`; `dandiset_id` |
| `AllenCellTypes_search_specimens` | Single-neuron electrophysiology + morphology specimens (firing rate, input resistance, tau, reconstructions); filter by species/brain region | `species` (e.g. `"Homo Sapiens"`, `"Mus musculus"`), `brain_structure`, `limit` |
| `Alliance_search_genes` | Cross-species gene search (mouse, fly, fish, worm) | `query` |
| `UniProt_search` | Neural proteins (ion channels, receptors, disease genes) | `query`, `organism` |
| `proteins_api_search` | Protein features, domains, variants | `query` |
| `NCBIGene_search` | Gene info, orthologs, expression | `query` |
| `ClinVar_search_variants` | Neurological disease variants | `gene`, `condition` |
| `gwas_search_associations` | Neurological trait associations | `query` |
| `Orphanet_search_diseases` | Rare neurological diseases | `query` |
| `kegg_get_pathway_info` | Neural signaling pathways | `pathway_id` |
| `OpenTargets_multi_entity_search_by_query_string` | Drug targets in neurological diseases | `query` |

### Tool Selection Strategy
1. **Neuroanatomy question**: PubMed first — search "[structure] [function/connectivity]"
2. **Ion channel / receptor question**: UniProt — search protein name with organism
3. **Disease gene question**: ClinVar + GWAS + Orphanet
4. **Connectome / circuit question**: WormBase (C. elegans), PubMed (other organisms)
5. **Computational question**: Write Python code — do not guess numerical answers
6. **Clinical neurology question**: PubMed + reasoning frameworks above; verify anatomy before answering

---

## 6. C. elegans Connectome Lookups

For C. elegans neural circuit questions, ALWAYS use `WormBase_get_gene` to look up specific synapse and connectivity data. Do not guess neural connections from general knowledge.
- **ASJ neuron projections**: the main projection target of ASJ axons is PVQ (verified in WormBase connectome data), NOT AIA. Always check actual synapse counts rather than inferring from circuit diagrams.
- Search WormBase with the specific neuron name to get its pre/postsynaptic partners and projection targets.

## 7. Single-Neuron Morphology Lookups (NeuroMorpho)

For questions about a specific reconstructed neuron's shape, dendritic/axonal
morphology, or morphometric measurements, use the 7 NeuroMorpho.Org tools
instead of guessing typical values from general knowledge — this is a
database of 250,000+ digitally traced neuron reconstructions with precise
per-neuron quantitative measurements.

| Tool | Use For | Key Parameters |
|------|---------|---------------|
| `NeuroMorpho_search_neurons` | Find neurons by species/brain region/cell type/archive/stain | `query_field`, `query_value`, `filter_field`, `filter_value`, `size` |
| `NeuroMorpho_get_field_values` | Discover valid values for a search field before searching | `field_name` (e.g. `species`, `brain_region`, `cell_type`) |
| `NeuroMorpho_get_neuron` | Full metadata for one neuron: species, brain region, cell type, staining, reconstruction software, source publication | `neuron_id` or `neuron_name` |
| `NeuroMorpho_get_morphometry` | Quantitative shape measurements: surface area, volume, number of stems/bifurcations/branches, width/height/depth, total length, fractal dimension | `neuron_id` or `neuron_name` |
| `NeuroMorpho_get_persistence_vector` | 100-coefficient TMD (Topological Morphology Descriptor) shape signature, for ML clustering/classification of dendritic shape | `neuron_id` |
| `NeuroMorpho_search_literature` | Find the source publications behind reconstructions for a brain region/cell type/species | `query_field` (`brainRegion`, `cellType`, `species`, `tracingSystem`), `query_value` |
| `NeuroMorpho_get_literature` | Full citation record (DOI, PMID, journal, authors) for one source publication | `article_id` (from `NeuroMorpho_search_literature`) |

**Workflow**: `NeuroMorpho_search_neurons` (search results already include most
metadata fields — species, brain_region, cell_type, soma_surface, surface,
volume, reference_pmid, png_url — so a follow-up `NeuroMorpho_get_neuron` call
is often unnecessary unless you need a field the search response omits) ->
for quantitative measurements not in the search response (bifurcations,
branch count, fractal dimension, path/Euclidean distance), call
`NeuroMorpho_get_morphometry` on a specific `neuron_id` -> for the underlying
publication, take `reference_pmid` from the neuron record directly, or use
`NeuroMorpho_search_literature`/`NeuroMorpho_get_literature` to browse by
brain region/cell type rather than a specific neuron.

Verified live example: searching `species=human`, `brain_region=hippocampus`
returns 139 matches (e.g. neuron 147055, a human CA1 pyramidal cell, archive
DeFelipe); its morphometry gives `surface=40808.7 um^2`, `volume=15367.3 um^3`,
`n_bifs=76`, `length=11305.5 um`, `fractal_Dim=1.024`.

## 8. Neuroimaging Dataset Discovery (OpenNeuro)

For finding published, BIDS-formatted neuroimaging datasets (MRI, fMRI, EEG,
iEEG, MEG, PET) — as opposed to `DANDI` (electrophysiology/imaging in NWB
format, already listed above) — use the 7 OpenNeuro tools. OpenNeuro hosts
1600+ datasets; do not assume a dataset with the "right" ID exists without
checking, and do not guess at file names — always resolve them through
`OpenNeuro_get_snapshot_files`.

| Tool | Use For | Key Parameters |
|------|---------|---------------|
| `OpenNeuro_list_datasets` | Browse the newest public datasets, cursor-paginated | `first` (max 25), `after` (cursor) |
| `OpenNeuro_search_by_modality` | Filter datasets by imaging modality | `modality` (`MRI`, `EEG`, `iEEG`, `MEG`, `PET`), `first` |
| `OpenNeuro_advanced_search` | Faceted search (species, sex, diagnosis, task, scanner manufacturer, PET tracer, age/subject-count range) plus the archive-wide total participant count | any combination of facet args; omit all for a whole-archive count |
| `OpenNeuro_get_dataset` | Full metadata for one dataset: modalities, subjects, tasks, BIDS version, authors, DOI, README | `datasetId` (e.g. `ds000117`) |
| `OpenNeuro_get_dataset_snapshots` | List every published version (snapshot tag) of a dataset | `datasetId` |
| `OpenNeuro_get_snapshot_files` | File manifest with direct download URLs for one specific version | `datasetId`, `tag` (from the snapshots call) |
| `OpenNeuro_get_snapshot_validation` | BIDS-validator error/warning counts for one version, to check quality before downloading | `datasetId`, `tag` |

**Workflow**: `OpenNeuro_search_by_modality` or `OpenNeuro_advanced_search` to
find a candidate dataset ID -> `OpenNeuro_get_dataset` for its
modalities/subjects/tasks/README (dataset-level metadata only — no file
list) -> `OpenNeuro_get_dataset_snapshots` to get a specific version tag ->
`OpenNeuro_get_snapshot_files` for the actual downloadable file manifest, or
`OpenNeuro_get_snapshot_validation` to check BIDS-compliance first.

**Gotcha (verified live)**: `OpenNeuro_advanced_search` with a facet filter
can report a nonzero `pageInfo.count` while returning an empty `edges` list —
per the tool's own description, some matched datasets aren't anonymously
readable, so the count stays accurate even when the ID list is incomplete.
Don't treat an empty `edges` array as "count is wrong" or "no datasets
exist" when `pageInfo.count` says otherwise.

Verified live example: `ds000117` ("Multisubject, multimodal face
processing") has 13 published snapshot versions (`00001`-`00004`, `1.0.0`
through `1.0.6`, `1.1.0`, `2.0.0`); its latest snapshot spans MRI+MEG
modalities, 17 subjects, 2 tasks (`facerecognition`, `noise`), 1157 total
files, ~90 GB.

## 9. Computational Model Lookups (ModelDB)

For finding or comparing published computational neuroscience models
(equation-level simulations — e.g. Hodgkin-Huxley-style single-neuron models,
network models) rather than experimental data, use the 5 ModelDB (Yale/
SenseLab) tools instead of guessing what a "standard" model of a given cell
type looks like. ModelDB links each model to its source publication and to
the specific neuron/cell types it simulates.

| Tool | Use For | Key Parameters |
|------|---------|---------------|
| `ModelDB_list_models` | Discover model IDs, optionally filtered by simulator | `modeling_application` (e.g. `NEURON`, `GENESIS`, `Python`, `MATLAB`, `Brian`, `NEST`, `XPP`, `C or C++`) — case-sensitive, omit for all 1000+ models |
| `ModelDB_get_model` | Full model detail: description/notes, neuron types modeled, ion currents, model concepts, simulator, linked paper(s), implementer | `model_id` (integer) |
| `ModelDB_get_paper` | Full citation for a model's source publication (title, authors, journal, PubMed ID, DOI) | `paper_id` (integer, from `model_paper` in a model record) |
| `ModelDB_list_celltypes` | Discover the neuron/cell-type IDs ModelDB categorizes models by | none |
| `ModelDB_get_celltype` | Name and metadata for one cell type (e.g. "Hippocampus CA3 pyramidal GLU cell") — note the response can include a large embedded base64 image under `Picture`, don't print it verbatim | `celltype_id` (string, from `ModelDB_list_celltypes` or a model's `neurons` field) |

**Workflow**: `ModelDB_list_models` (optionally filtered by simulator) -> pick
a real ID -> `ModelDB_get_model` for full detail, including the ion currents
and `model_concept` tags (e.g. "Bursting", "Detailed Neuronal Models") -> take
the `object_id` from `model_paper` and call `ModelDB_get_paper` for the
citation and PubMed ID -> take an `object_id` from the model's `neurons`
field and call `ModelDB_get_celltype` for the modeled cell type's description.

Verified live example: model 3263 is "CA3 Pyramidal Neuron (Migliore et al
1995)", a NEURON-simulator model with 9 ion currents (I Na,t / I L high
threshold / I N / I T low threshold / I A / I K / I M / I K,Ca / I Calcium),
tagged "Bursting" and "Detailed Neuronal Models", linking to paper 4307
(Migliore et al., J Neurophysiol 73:1157-1168, 1995, PubMed 7608762) and cell
type 259 ("Hippocampus CA3 pyramidal GLU cell").

## 10. Neuroimaging Statistical Map Discovery (NeuroVault)

For finding published, group-level statistical brain maps (fMRI/PET
activation maps, anatomical atlases/parcellations) — DERIVED analysis
results, not raw scans (compare to OpenNeuro above, which hosts the raw BIDS
data those maps were computed from) — use the 6 NeuroVault tools.

**Caveat, verified live**: NeuroVault's public API has no working keyword/
name search — `name`/`search`/`q`/`keywords` parameters all silently return
the full unfiltered catalog (17,862+ collections) rather than filtering. The
only practical way to find a specific study is to already know its
collection/image ID (e.g. from the paper itself or the NeuroVault website),
or to page through `NeuroVault_list_collections` client-side. Don't imply a
working search exists.

| Tool | Use For | Key Parameters |
|------|---------|---------------|
| `NeuroVault_list_collections` | Page through the full collection catalog (no real filtering — see caveat) | `limit` (max 100), `offset` |
| `NeuroVault_get_collection` | Full study metadata for one collection: DOI, authors, journal, scanner/field-strength/pulse-sequence, image count | `collection_id` |
| `NeuroVault_list_collection_images` | List the statistical map images in one collection, with map type and Cognitive Atlas paradigm/contrast labels | `collection_id`, `limit`, `offset` |
| `NeuroVault_get_image` | Full metadata for one statistical map: map type (T/Z/F/beta/ROI/parcellation), modality, cognitive paradigm/contrast, NIfTI download URL, subject count | `image_id` |
| `NeuroVault_list_atlases` | Browse labeled anatomical parcellation maps (18 total) | `limit`, `offset` |
| `NeuroVault_get_atlas` | One atlas's label-image URL plus its label-description file (names each parcel/region) | `atlas_id` |

**Workflow**: if you already know a collection ID (e.g. cited in a paper) ->
`NeuroVault_get_collection` for study metadata -> `NeuroVault_list_collection_images`
to see what maps are available -> `NeuroVault_get_image` on a specific image
for its Cognitive-Atlas contrast label and NIfTI download URL. For anatomical
labels/parcellations rather than task activation maps, use
`NeuroVault_list_atlases` -> `NeuroVault_get_atlas`.

Verified live example: collection 457 is "The WU-Minn Human Connectome
Project: An overview" (DOI 10.1016/j.neuroimage.2013.05.041, 48 images);
image 3128 in that collection is a Z map, "tfMRI EMOTION FACES minus SHAPES
zstat1", Cognitive Atlas paradigm "emotion processing fMRI task paradigm",
modality fMRI-BOLD, 486 subjects, MNI space.

## 11. Choosing Among the Four Neuroscience Data Resources

This skill now covers four distinct external neuroscience data resources —
pick based on what kind of object you actually need:

| Resource | What it holds | Example question |
|----------|---------------|-------------------|
| **NeuroMorpho** (Sec. 7) | Digitally reconstructed single-neuron morphology (dendrite/axon shape, measured from real tissue) | "What's the total dendritic length of a human CA1 pyramidal cell?" |
| **OpenNeuro** (Sec. 8) | Raw, BIDS-formatted neuroimaging datasets (MRI/fMRI/EEG/MEG/PET scans, not yet analyzed) | "Is there a public multimodal face-processing MEG+MRI dataset I can reanalyze?" |
| **ModelDB** (Sec. 9) | Published computational models (equations/parameters implementing a simulated neuron or network) | "Is there an existing NEURON-simulator model of a bursting CA3 pyramidal cell I can build on?" |
| **NeuroVault** (Sec. 10) | Derived group-level statistical brain maps (post-analysis results: activation maps, atlases) from published studies | "Where's the group-level activation map for the emotion-processing contrast from the HCP paper?" |

Also see `DANDI` (Sec. 5, Available Tools) for raw electrophysiology/imaging
in NWB format and `AllenCellTypes_search_specimens` for single-neuron
electrophysiology+morphology specimens — a fifth and sixth resource type
already documented above.

For a different kind of question entirely — "what cognitive function is
this MNI coordinate associated with?" or "which studies/coordinates are
linked to this term?" — none of the six resources above hold what you need;
that's coordinate-based meta-analytic decoding over ~14,000 published fMRI
studies, covered by the separate `tooluniverse-neurosynth-meta-analysis`
skill.

## 12. Common Pitfalls

- **Confusing brain regions**: The hippocampus is NOT in the frontal lobe. The substantia nigra is in the midbrain, NOT the basal ganglia (though functionally linked). Always verify.
- **Mixing up neurotransmitter receptors**: GABA_A is ionotropic (Cl-), GABA_B is metabotropic (G-protein). NMDA requires both glutamate AND glycine/D-serine co-agonist.
- **Wrong units in computation**: Membrane time constants are in ms (not seconds). Firing rates are in Hz (spikes/s). Conductances are in nS or mS/cm2.
- **Assuming all neurons fire fast**: Cortical neurons fire at 1-20 Hz on average; only specific cell types (e.g., fast-spiking interneurons) sustain >100 Hz.
- **Ignoring lateralization**: Language is left-lateralized in ~95% of right-handers. Spatial attention is right-lateralized. Always consider which hemisphere.
