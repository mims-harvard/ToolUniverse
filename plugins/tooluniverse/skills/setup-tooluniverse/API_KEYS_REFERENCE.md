# ToolUniverse API Keys Reference

Detailed guide for every API key used by ToolUniverse. Use this when walking users through key setup.

---

## Tier 1: Core Scientific Keys

### NCBI_API_KEY

- **Service**: NCBI (National Center for Biotechnology Information) / PubMed
- **Required**: No (optional, but strongly recommended)
- **Tools that use it**: `PubMed_search_articles`, `PubMed_get_article`, and 3 more PubMed tools
- **What it does**: Increases PubMed API rate limit from 3 requests/second to 10 requests/second. Without it, heavy literature searches may be throttled.
- **How to get it**:
  1. Go to https://account.ncbi.nlm.nih.gov/ and sign in (via Google, ORCiD, eRA Commons, or Login.gov)
  2. Go to Settings at https://account.ncbi.nlm.nih.gov/settings/
  3. Scroll to "API Key Management" at the bottom
  4. Click "Create an API Key"
  5. Copy the generated key
- **Env variable**: `NCBI_API_KEY`

### NVIDIA_API_KEY

- **Service**: NVIDIA NIM (NVIDIA Inference Microservices)
- **Required**: Yes (for NIM tools)
- **Tools that use it**: 16 `NvidiaNIM_*` tools including AlphaFold2 structure prediction, molecular docking (DiffDock), ESM protein embeddings, and genomics tools
- **What it does**: Provides access to GPU-accelerated bioinformatics models hosted by NVIDIA. Covers protein structure prediction, molecular docking, and sequence analysis.
- **How to get it**:
  1. Go to https://build.nvidia.com
  2. Sign in or create a free NVIDIA account
  3. Navigate to any NIM API (e.g., AlphaFold2)
  4. Click "Get API Key" in the top right
  5. Copy the key (starts with `nvapi-`)
- **Env variable**: `NVIDIA_API_KEY`
- **Free tier**: Yes, generous free credits for API calls

### BIOGRID_API_KEY

- **Service**: BioGRID (Biological General Repository for Interaction Datasets)
- **Required**: Yes (tools will not work without it)
- **Tools that use it**: `BioGRID_get_interactions`
- **What it does**: Enables querying the BioGRID database for protein-protein interactions, genetic interactions, and chemical associations.
- **How to get it**:
  1. Go to https://webservice.thebiogrid.org/
  2. Click "Register" to create a free account
  3. After registration, your API access key will be provided
  4. You can also find it under your account settings
- **Env variable**: `BIOGRID_API_KEY`

### DISGENET_API_KEY

- **Service**: DisGeNET (Disease-Gene Network)
- **Required**: Yes (tools will not work without it)
- **Tools that use it**: 5 DisGeNET tools for gene-disease associations, variant-disease associations, and disease enrichment analysis
- **What it does**: Provides access to one of the largest collections of gene-disease associations, integrating data from expert-curated repositories, GWAS catalogs, and animal models.
- **How to get it**:
  1. Go to https://disgenet.com/academic-apply (for academic/non-profit use)
  2. Fill out the application with your institutional email
  3. Verify your email within 24 hours
  4. Wait for approval (typically within 7 days)
  5. Once approved, find your API key in your account settings
- **Env variable**: `DISGENET_API_KEY`
- **Note**: Free for academic use; commercial use requires a license

---

## Tier 2: Specialized Scientific Keys

### OMIM_API_KEY

- **Service**: OMIM (Online Mendelian Inheritance in Man)
- **Required**: Yes (tools will not work without it)
- **Tools that use it**: 4 OMIM tools for Mendelian disease data, gene-phenotype relationships, and clinical synopses
- **What it does**: Provides access to the authoritative database of human genes and genetic phenotypes, particularly for inherited diseases.
- **How to get it**:
  1. Go to https://omim.org/api
  2. Click "Request API Key"
  3. Fill out the registration form (academic/institutional email recommended)
  4. API key is typically emailed within 1-2 business days
- **Env variable**: `OMIM_API_KEY`
- **Note**: Approval may take time; academic users are prioritized

### ONCOKB_API_TOKEN

- **Service**: OncoKB (Precision Oncology Knowledge Base)
- **Required**: Yes (tools will not work without it)
- **Tools that use it**: OncoKB tools for cancer gene annotations, actionable mutations, and therapeutic implications
- **What it does**: Provides access to MSK's precision oncology knowledge base with FDA-recognized biomarker-drug associations, levels of evidence for therapeutic implications.
- **How to get it**:
  1. Go to https://www.oncokb.org/apiAccess
  2. Click "Request API Access"
  3. Register with your institutional email
  4. For academic use, select the free academic license
  5. Token is provided after approval
- **Env variable**: `ONCOKB_API_TOKEN`
- **Note**: Free for academic/research use

### UMLS_API_KEY

- **Service**: UMLS (Unified Medical Language System) / NLM
- **Required**: Yes (tools will not work without it)
- **Tools that use it**: 5 UMLS tools for medical concept lookup, terminology mapping, cross-referencing between medical vocabularies (ICD, SNOMED, MeSH, etc.)
- **What it does**: Maps between medical terminologies, finds concept definitions, and navigates hierarchical relationships between medical concepts.
- **How to get it**:
  1. Go to https://uts.nlm.nih.gov/uts/
  2. Click "Sign Up" to create a UMLS Terminology Services account
  3. You'll need to accept the UMLS license agreement
  4. After approval, go to "My Profile" to find your API key
- **Env variable**: `UMLS_API_KEY`
- **Note**: Requires license agreement acceptance; usually instant for US-based users

### USPTO_API_KEY

- **Service**: USPTO (United States Patent and Trademark Office)
- **Required**: Yes (tools will not work without it)
- **Tools that use it**: 6 USPTO tools for patent search, patent data retrieval, and patent analysis
- **What it does**: Enables searching and retrieving US patent documents, patent claims, and patent family information.
- **How to get it**:
  1. Create a USPTO account at https://my.uspto.gov/ (if you don't have one)
  2. Go to the API manager at https://account.uspto.gov/api-manager/
  3. Log in with your USPTO credentials
  4. Register for an API key -- it will be emailed to you
- **Env variable**: `USPTO_API_KEY`

### SEMANTIC_SCHOLAR_API_KEY

- **Service**: Semantic Scholar (Allen Institute for AI)
- **Required**: No (optional, but recommended for heavy literature use)
- **Tools that use it**: `SemanticScholar_search_papers`
- **What it does**: Increases rate limit from 1 request/second to 100 requests/second. Essential if doing bulk literature searches or citation analysis.
- **How to get it**:
  1. Go to https://www.semanticscholar.org/product/api
  2. Click "Request API Key"
  3. Fill out the form with your use case
  4. Key is typically emailed within a few days
- **Env variable**: `SEMANTIC_SCHOLAR_API_KEY`

### FDA_API_KEY

- **Service**: openFDA
- **Required**: No (optional, raises rate limits)
- **Tools that use it**: OpenFDA tools and FAERS adverse event analytics
- **What it does**: Increases openFDA rate limit from 240 requests/minute to 1000 requests/minute. Useful for drug safety signal analysis.
- **How to get it**:
  1. Go to https://open.fda.gov/apis/authentication/
  2. Enter your email to request a key
  3. Key is emailed instantly
- **Env variable**: `FDA_API_KEY`

### BRENDA_EMAIL + BRENDA_PASSWORD

- **Service**: BRENDA (Braunschweig Enzyme Database)
- **Required**: Yes (tools will not work without both)
- **Tools that use it**: 3 BRENDA tools for enzyme kinetics, substrate specificity, and enzyme functional data
- **What it does**: Provides access to the world's most comprehensive enzyme database with kinetic parameters (Km, Vmax, kcat), substrate/product data, and enzyme classifications.
- **How to get it**:
  1. Go to https://brenda-enzymes.org/register.php
  2. Fill in email, password, name, and scientific field
  3. Complete the captcha and submit
  4. Confirm your email
  5. Use the email and password you registered with as the API credentials
- **Env variables**: `BRENDA_EMAIL` and `BRENDA_PASSWORD`
- **Note**: This uses your login credentials, not a separate API key

### MOUSER_API_KEY

- **Service**: Mouser Electronics
- **Required**: Yes (tools will not work without it)
- **Tools that use it**: 4 Mouser tools for electronic component search by keyword, part number, and manufacturer
- **What it does**: Provides access to Mouser's comprehensive catalog of electronic components, including ICs, resistors, capacitors, microcontrollers, and more. Includes pricing, availability, datasheets, and specifications.
- **How to get it**:
  1. Go to https://www.mouser.com/api-search/
  2. Click "Sign Up For Search API"
  3. Fill out the registration form (requires business/academic email)
  4. API key is typically provided instantly after email verification
- **Env variable**: `MOUSER_API_KEY`
- **Free tier**: Yes, 1,000 requests/day, 30 requests/minute

### DIGIKEY_CLIENT_ID + DIGIKEY_CLIENT_SECRET

- **Service**: Digi-Key Electronics
- **Required**: Yes (tools will not work without both)
- **Tools that use it**: 4 Digi-Key tools for product search, detailed product info, category browsing, and manufacturer listings
- **What it does**: Provides access to Digi-Key's extensive catalog of electronic components with detailed specifications, pricing, inventory, parametric search, and technical documentation.
- **How to get it**:
  1. Go to https://developer.digikey.com/
  2. Click "Register" to create a free developer account
  3. After login, go to "Organization" → "Production Apps"
  4. Click "Create Production App"
  5. Fill in app details (name, description, OAuth callback URL: `https://localhost/callback`)
  6. After creation, copy the **Client ID** and **Client Secret**
- **Env variables**: `DIGIKEY_CLIENT_ID` and `DIGIKEY_CLIENT_SECRET`
- **Free tier**: Yes, 1,000 requests/day, 120 requests/minute
- **Note**: Uses OAuth2 authentication with automatic token refresh. The tool handles token management automatically.

---

## Tier 3: LLM Provider Keys

These keys power ToolUniverse's **agentic features** -- tools that use LLMs to synthesize results, plan multi-step analyses, and generate reports. At least one LLM provider key is needed for these features.

The system checks providers in this order: **Azure OpenAI -> OpenRouter -> Gemini**. Configure whichever you prefer.

### GEMINI_API_KEY

- **Service**: Google Gemini
- **Required**: No (one of the LLM providers needed for agentic features)
- **What it does**: Powers agentic tools using Google's Gemini models. Good default choice due to generous free tier.
- **How to get it**:
  1. Go to https://aistudio.google.com/apikey
  2. Sign in with your Google account
  3. Click "Create API Key" (a default Google Cloud project is created automatically for new users)
  4. Copy the key
- **Env variable**: `GEMINI_API_KEY`
- **Free tier**: Yes, generous free usage limits

### OPENROUTER_API_KEY

- **Service**: OpenRouter
- **Required**: No (alternative LLM provider)
- **What it does**: Provides access to 100+ LLM models through a single API. Pay-per-use pricing, good flexibility.
- **How to get it**:
  1. Go to https://openrouter.ai/
  2. Sign up or log in
  3. Go to https://openrouter.ai/keys
  4. Click "Create Key"
  5. Add credits to your account for usage
- **Env variable**: `OPENROUTER_API_KEY`

### OPENAI_API_KEY

- **Service**: OpenAI
- **Required**: No (alternative LLM provider, also used for embeddings)
- **What it does**: Powers embedding-based tool finding and can serve as an LLM provider for agentic features.
- **How to get it**:
  1. Go to https://platform.openai.com/
  2. Sign up or log in
  3. Go to API Keys section
  4. Click "Create new secret key"
  5. Copy the key (starts with `sk-`)
- **Env variable**: `OPENAI_API_KEY`

### AZURE_OPENAI_API_KEY

- **Service**: Azure OpenAI Service
- **Required**: No (enterprise alternative to direct OpenAI)
- **What it does**: Same capabilities as OpenAI but through Azure infrastructure. Preferred for enterprise/institutional users.
- **How to get it**:
  1. Go to Azure Portal (https://portal.azure.com)
  2. Create or navigate to your Azure OpenAI resource
  3. Go to "Keys and Endpoint" in the resource
  4. Copy Key 1 or Key 2
- **Env variables**: `AZURE_OPENAI_API_KEY` and optionally `AZURE_OPENAI_ENDPOINT`
- **Note**: Also set `AZURE_OPENAI_ENDPOINT` if not using the default endpoint

### ANTHROPIC_API_KEY

- **Service**: Anthropic (Claude)
- **Required**: No (alternative LLM provider)
- **What it does**: Enables Claude-based features.
- **How to get it**:
  1. Go to https://console.anthropic.com/
  2. Sign up or log in
  3. Go to API Keys section
  4. Create a new key
- **Env variable**: `ANTHROPIC_API_KEY`

### HF_TOKEN

- **Service**: HuggingFace
- **Required**: No (optional, for model/dataset access)
- **What it does**: Enables access to gated HuggingFace models and datasets, and the HF Inference API for embeddings.
- **How to get it**:
  1. Go to https://huggingface.co/settings/tokens
  2. Sign up or log in
  3. Click "New token"
  4. Select "Read" access (sufficient for most uses)
  5. Copy the token (starts with `hf_`)
- **Env variable**: `HF_TOKEN`
- **Free tier**: Yes

---

## Quick Setup by Research Area

| Research Area | Recommended Keys |
|---|---|
| **Literature/publications** | `NCBI_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY` |
| **Drug discovery** | `NVIDIA_API_KEY`, `DISGENET_API_KEY`, `BIOGRID_API_KEY` |
| **Protein structure** | `NVIDIA_API_KEY` |
| **Rare diseases** | `OMIM_API_KEY`, `DISGENET_API_KEY`, `UMLS_API_KEY` |
| **Oncology** | `ONCOKB_API_TOKEN`, `DISGENET_API_KEY` |
| **Enzymology** | `BRENDA_EMAIL` + `BRENDA_PASSWORD` |
| **Drug safety** | `FDA_API_KEY`, `UMLS_API_KEY` |
| **Patents** | `USPTO_API_KEY` |
| **Electronic components/IC design** | `MOUSER_API_KEY`, `DIGIKEY_CLIENT_ID` + `DIGIKEY_CLIENT_SECRET` |
| **AI-powered analysis** | Any one of: `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `OPENAI_API_KEY` |
| **Full setup (all features)** | All Tier 1 + relevant Tier 2 + one Tier 3 key |
