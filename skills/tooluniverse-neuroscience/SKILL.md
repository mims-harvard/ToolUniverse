---
name: tooluniverse-neuroscience
description: Neuroscience research and reasoning workflows using ToolUniverse tools. Covers computational neuroscience (rate models, integrate-and-fire neurons, synaptic plasticity, network dynamics), neuroanatomy (cortical regions, basal ganglia, cerebellum, brainstem, model organism connectomes), neurophysiology (ion channels, action potentials, synaptic transmission), neural circuits (E/I balance, oscillations, central pattern generators), synaptic dynamics (STDP, short-term plasticity, neuromodulation), neurodegenerative diseases (Alzheimer's, Parkinson's, ALS, Huntington's), and clinical neurology (cranial nerves, stroke localization, neuromuscular disorders). Use when researchers ask about brain regions, neural computation, firing rates, synaptic plasticity, connectomics, neurodegeneration, or clinical neurological questions.
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
- **C. elegans**: 302 neurons, complete connectome mapped; use `WormBase_search` for gene expression, neuron identity, connectivity data
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
| `WormBase_search` | C. elegans neurons, connectome, gene expression | `query` |
| `Alliance_search_genes` | Cross-species gene search (mouse, fly, fish, worm) | `query` |
| `UniProt_search` | Neural proteins (ion channels, receptors, disease genes) | `query`, `organism` |
| `proteins_api_search` | Protein features, domains, variants | `query` |
| `NCBI_search_gene` | Gene info, orthologs, expression | `query` |
| `ClinVar_search_variants` | Neurological disease variants | `gene`, `condition` |
| `GWAS_search_associations` | Neurological trait associations | `query` |
| `Orphanet_search_diseases` | Rare neurological diseases | `query` |
| `KEGG_get_pathway` | Neural signaling pathways | `pathway_id` |
| `OpenTargets_search_target` | Drug targets in neurological diseases | `query` |

### Tool Selection Strategy
1. **Neuroanatomy question**: PubMed first — search "[structure] [function/connectivity]"
2. **Ion channel / receptor question**: UniProt — search protein name with organism
3. **Disease gene question**: ClinVar + GWAS + Orphanet
4. **Connectome / circuit question**: WormBase (C. elegans), PubMed (other organisms)
5. **Computational question**: Write Python code — do not guess numerical answers
6. **Clinical neurology question**: PubMed + reasoning frameworks above; verify anatomy before answering

---

## 6. C. elegans Connectome Lookups

For C. elegans neural circuit questions, ALWAYS use `WormBase_search` to look up specific synapse and connectivity data. Do not guess neural connections from general knowledge.
- **ASJ neuron projections**: the main projection target of ASJ axons is PVQ (verified in WormBase connectome data), NOT AIA. Always check actual synapse counts rather than inferring from circuit diagrams.
- Search WormBase with the specific neuron name to get its pre/postsynaptic partners and projection targets.

## 7. Common Pitfalls

- **Confusing brain regions**: The hippocampus is NOT in the frontal lobe. The substantia nigra is in the midbrain, NOT the basal ganglia (though functionally linked). Always verify.
- **Mixing up neurotransmitter receptors**: GABA_A is ionotropic (Cl-), GABA_B is metabotropic (G-protein). NMDA requires both glutamate AND glycine/D-serine co-agonist.
- **Wrong units in computation**: Membrane time constants are in ms (not seconds). Firing rates are in Hz (spikes/s). Conductances are in nS or mS/cm2.
- **Assuming all neurons fire fast**: Cortical neurons fire at 1-20 Hz on average; only specific cell types (e.g., fast-spiking interneurons) sustain >100 Hz.
- **Ignoring lateralization**: Language is left-lateralized in ~95% of right-handers. Spatial attention is right-lateralized. Always consider which hemisphere.
