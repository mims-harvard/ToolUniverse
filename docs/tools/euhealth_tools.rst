Euhealth Tools
==============

**Configuration File**: ``euhealth_tools.json``
**Tool Type**: Local
**Tools Count**: 21

This page contains all tools defined in the ``euhealth_tools.json`` configuration file.

Available Tools
---------------

**euhealthinfo_deepdive** (Type: EuHealthDeepDiveTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This tool identifies and retrieves relevant links related to publicly accessible datasets and inf...

.. dropdown:: euhealthinfo_deepdive tool specification

   **Tool Information:**

   * **Name**: ``euhealthinfo_deepdive``
   * **Type**: ``EuHealthDeepDiveTool``
   * **Description**: This tool identifies and retrieves relevant links related to publicly accessible datasets and information sources. Using metadata or topic-specific queries, it generates structured outputs of categorized links, including direct download pages, resource portals, and other associated materials. When metadata is unavailable or incomplete, the tool dynamically navigates query results to provide actionable outputs. It also classifies links by type and provides additional contextual details, ensuring users can access pertinent resources for their informational needs.

   **Parameters:**

   * ``uuids`` (array) (optional)
     Dataset UUIDs to deep-dive (format 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'). If provided, the tool inspects exactly these datasets.

   * ``topic`` (string) (optional)
     Topic name to resolve seeds from (e.g., 'euhealthinfo_search_cancer'). Used when 'uuids' are not provided.

   * ``limit`` (integer) (optional)
     Maximum number of datasets to resolve when using 'topic'. Default 10.

   * ``links_per`` (integer) (optional)
     Maximum number of outgoing links to classify per dataset. Default 3.

   * ``country`` (string) (optional)
     Country filter applied when resolving seeds from 'topic'. Accepts full names (e.g., 'Germany') or ISO-3166 codes ('DE', 'DEU'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``language`` (string) (optional)
     Language filter applied when resolving seeds from 'topic'. Accepts ISO 639-1 codes (e.g., 'en') or full names (e.g., 'English'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``term_override`` (string) (optional)
     Overrides the default topic seed terms with a custom query string when using 'topic'.

   * ``method`` (string) (optional)
     Search strategy used when resolving from topic (ignored if 'uuids' are given).

   * ``alpha`` (number) (optional)
     Blend ratio used when method='hybrid'.

   * ``top_k`` (integer) (optional)
     Number of candidate documents to retrieve before filtering.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "euhealthinfo_deepdive",
          "arguments": {
          }
      }
      result = tu.run(query)


**euhealthinfo_search_alcohol_tobacco_psychoactive_use** (Type: EuHealthTopicSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This tool provides centralized access to datasets focused on substance usage, including alcohol, ...

.. dropdown:: euhealthinfo_search_alcohol_tobacco_psychoactive_use tool specification

   **Tool Information:**

   * **Name**: ``euhealthinfo_search_alcohol_tobacco_psychoactive_use``
   * **Type**: ``EuHealthTopicSearchTool``
   * **Description**: This tool provides centralized access to datasets focused on substance usage, including alcohol, tobacco, vaping, and psychoactive substances. It enables users to investigate behavioral trends, societal perceptions, and related impacts by retrieving both metadata and dataset links, offering a streamlined gateway to resources for population-level analysis and study of substance-use patterns. If the user wants to look into the actual data, the 'euhealthinfo_deepdive' tool is helpful.

   **Parameters:**

   * ``limit`` (integer) (optional)
     Maximum number of results to return. Default 25.

   * ``country`` (string) (optional)
     Country filter. Accepts full names (e.g., 'Germany') or ISO-3166 codes ('DE', 'DEU'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``language`` (string) (optional)
     Language filter. Accepts ISO 639-1 codes (e.g., 'en') or full names (e.g., 'English'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``term_override`` (string) (optional)
     Override the default topic seed terms with a custom query string. Defaults internally to 'search alcohol/tobacco psychoactive use'.

   * ``method`` (string) (optional)
     Search strategy: 'keyword' (text only), 'embedding' (vector), or 'hybrid' (blend).

   * ``alpha`` (number) (optional)
     Blend ratio used when method='hybrid' (0=text, 1=embedding).

   * ``top_k`` (integer) (optional)
     Number of candidate documents to retrieve before filtering.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "euhealthinfo_search_alcohol_tobacco_psychoactive_use",
          "arguments": {
          }
      }
      result = tu.run(query)


**euhealthinfo_search_births** (Type: EuHealthTopicSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This tool identifies and retrieves data related to fertility, birth trends, and perinatal indicat...

.. dropdown:: euhealthinfo_search_births tool specification

   **Tool Information:**

   * **Name**: ``euhealthinfo_search_births``
   * **Type**: ``EuHealthTopicSearchTool``
   * **Description**: This tool identifies and retrieves data related to fertility, birth trends, and perinatal indicators for use in structured analysis. It generates metadata or summary outputs designed for comparisons across geographical regions or countries, providing a foundation for statistical or demographic exploration. If the user wants to look into the actual data, the 'euhealthinfo_deepdive' tool is helpful.

   **Parameters:**

   * ``limit`` (integer) (optional)
     Maximum number of results to return. Default 25.

   * ``country`` (string) (optional)
     Country filter. Accepts full names (e.g., 'Germany') or ISO-3166 codes ('DE', 'DEU'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``language`` (string) (optional)
     Language filter. Accepts ISO 639-1 codes (e.g., 'en') or full names (e.g., 'English'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``term_override`` (string) (optional)
     Override the default topic seed terms with a custom query string. Defaults internally to 'births'.

   * ``method`` (string) (optional)
     Search strategy: 'keyword' (text only), 'embedding' (vector), or 'hybrid' (blend).

   * ``alpha`` (number) (optional)
     Blend ratio used when method='hybrid' (0=text, 1=embedding).

   * ``top_k`` (integer) (optional)
     Number of candidate documents to retrieve before filtering.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "euhealthinfo_search_births",
          "arguments": {
          }
      }
      result = tu.run(query)


**euhealthinfo_search_cancer** (Type: EuHealthTopicSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This tool provides a curated list of datasets and resources relevant to cancer-related topics, in...

.. dropdown:: euhealthinfo_search_cancer tool specification

   **Tool Information:**

   * **Name**: ``euhealthinfo_search_cancer``
   * **Type**: ``EuHealthTopicSearchTool``
   * **Description**: This tool provides a curated list of datasets and resources relevant to cancer-related topics, including detailed information on incidence, prevalence, survival rates, screening, and tumor registries. It analyzes data from a cached database and presents structured output featuring dataset summaries, metadata, identifiers, and other relevant attributes for users to explore cancer-related data across various contexts and regions. If the user wants to look into the actual data, the 'euhealthinfo_deepdive' tool is helpful.

   **Parameters:**

   * ``limit`` (integer) (optional)
     Maximum number of results to return. Default 25.

   * ``country`` (string) (optional)
     Country filter. Accepts full names (e.g., 'Germany') or ISO-3166 codes ('DE', 'DEU'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``language`` (string) (optional)
     Language filter. Accepts ISO 639-1 codes (e.g., 'en') or full names (e.g., 'English'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``term_override`` (string) (optional)
     Override the default topic seed terms with a custom query string. Defaults internally to 'cancer'

   * ``method`` (string) (optional)
     Search strategy: 'keyword' (text only), 'embedding' (vector), or 'hybrid' (blend).

   * ``alpha`` (number) (optional)
     Blend ratio used when method='hybrid' (0=text, 1=embedding).

   * ``top_k`` (integer) (optional)
     Number of candidate documents to retrieve before filtering.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "euhealthinfo_search_cancer",
          "arguments": {
          }
      }
      result = tu.run(query)


**euhealthinfo_search_cancer_registry** (Type: EuHealthTopicSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This tool identifies and retrieves datasets containing cancer-related statistical information. It...

.. dropdown:: euhealthinfo_search_cancer_registry tool specification

   **Tool Information:**

   * **Name**: ``euhealthinfo_search_cancer_registry``
   * **Type**: ``EuHealthTopicSearchTool``
   * **Description**: This tool identifies and retrieves datasets containing cancer-related statistical information. It is designed to assist users in exploring resources about cancer incidence, prevalence, mortality, and survival across various geographic, linguistic, and thematic contexts. The tool provides links to relevant datasets and accompanying metadata to support further examination and utilization. If the user wants to look into the actual data, the 'euhealthinfo_deepdive' tool is helpful.

   **Parameters:**

   * ``limit`` (integer) (optional)
     Maximum number of results to return. Default 25.

   * ``country`` (string) (optional)
     Country filter. Accepts full names (e.g., 'Germany') or ISO-3166 codes ('DE', 'DEU'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``language`` (string) (optional)
     Language filter. Accepts ISO 639-1 codes (e.g., 'en') or full names (e.g., 'English'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``term_override`` (string) (optional)
     Override the default topic seed terms with a custom query string. Defaults internally to 'cancer registry'.

   * ``method`` (string) (optional)
     Search strategy: 'keyword' (text only), 'embedding' (vector), or 'hybrid' (blend).

   * ``alpha`` (number) (optional)
     Blend ratio used when method='hybrid' (0=text, 1=embedding).

   * ``top_k`` (integer) (optional)
     Number of candidate documents to retrieve before filtering.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "euhealthinfo_search_cancer_registry",
          "arguments": {
          }
      }
      result = tu.run(query)


**euhealthinfo_search_causes_of_death** (Type: EuHealthTopicSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This tool enables users to search and retrieve datasets that provide insights into cause-specific...

.. dropdown:: euhealthinfo_search_causes_of_death tool specification

   **Tool Information:**

   * **Name**: ``euhealthinfo_search_causes_of_death``
   * **Type**: ``EuHealthTopicSearchTool``
   * **Description**: This tool enables users to search and retrieve datasets that provide insights into cause-specific mortality data. It generates outputs that may include summaries of mortality trends, metadata, and links to external resources, helping users analyze patterns in public health data across different regions and countries. The tool is designed to support exploration of mortality-related information organized by standardized categorizations while maintaining regional or national specificity in its outputs. If the user wants to look into the actual data, the 'euhealthinfo_deepdive' tool is helpful.

   **Parameters:**

   * ``limit`` (integer) (optional)
     Maximum number of results to return. Default 25.

   * ``country`` (string) (optional)
     Country filter. Accepts full names (e.g., 'Germany') or ISO-3166 codes ('DE', 'DEU'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``language`` (string) (optional)
     Language filter. Accepts ISO 639-1 codes (e.g., 'en') or full names (e.g., 'English'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``term_override`` (string) (optional)
     Override the default topic seed terms with a custom query string. Defaults internally to 'causes of death'.

   * ``method`` (string) (optional)
     Search strategy: 'keyword' (text only), 'embedding' (vector), or 'hybrid' (blend).

   * ``alpha`` (number) (optional)
     Blend ratio used when method='hybrid' (0=text, 1=embedding).

   * ``top_k`` (integer) (optional)
     Number of candidate documents to retrieve before filtering.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "euhealthinfo_search_causes_of_death",
          "arguments": {
          }
      }
      result = tu.run(query)


**euhealthinfo_search_covid_19** (Type: EuHealthTopicSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This tool facilitates the discovery of datasets and resources relevant to COVID-19 or SARS-CoV-2....

.. dropdown:: euhealthinfo_search_covid_19 tool specification

   **Tool Information:**

   * **Name**: ``euhealthinfo_search_covid_19``
   * **Type**: ``EuHealthTopicSearchTool``
   * **Description**: This tool facilitates the discovery of datasets and resources relevant to COVID-19 or SARS-CoV-2. It enables users to efficiently locate information across diverse topics, such as vaccination, hospitalization, seroprevalence, and wastewater monitoring, and provides access to associated data sources or portals for further exploration. If the user wants to look into the actual data, the 'euhealthinfo_deepdive' tool is helpful.

   **Parameters:**

   * ``limit`` (integer) (optional)
     Maximum number of results to return. Default 25.

   * ``country`` (string) (optional)
     Country filter. Accepts full names (e.g., 'Germany') or ISO-3166 codes ('DE', 'DEU'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``language`` (string) (optional)
     Language filter. Accepts ISO 639-1 codes (e.g., 'en') or full names (e.g., 'English'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``term_override`` (string) (optional)
     Override the default topic seed terms with a custom query string. Defaults internally to 'covid-19'.

   * ``method`` (string) (optional)
     Search strategy: 'keyword' (text only), 'embedding' (vector), or 'hybrid' (blend).

   * ``alpha`` (number) (optional)
     Blend ratio used when method='hybrid' (0=text, 1=embedding).

   * ``top_k`` (integer) (optional)
     Number of candidate documents to retrieve before filtering.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "euhealthinfo_search_covid_19",
          "arguments": {
          }
      }
      result = tu.run(query)


**euhealthinfo_search_deaths** (Type: EuHealthTopicSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This tool facilitates the exploration and analysis of datasets related to mortality metrics, enab...

.. dropdown:: euhealthinfo_search_deaths tool specification

   **Tool Information:**

   * **Name**: ``euhealthinfo_search_deaths``
   * **Type**: ``EuHealthTopicSearchTool``
   * **Description**: This tool facilitates the exploration and analysis of datasets related to mortality metrics, enabling users to examine trends and comparisons across various geographic regions. It is designed to retrieve relevant datasets based on user queries, assisting in identifying patterns and addressing key questions about mortality outcomes. The tool functions consistently to provide structured outputs relevant to the requested queries. If the user wants to look into the actual data, the 'euhealthinfo_deepdive' tool is helpful.

   **Parameters:**

   * ``limit`` (integer) (optional)
     Maximum number of results to return. Default 25.

   * ``country`` (string) (optional)
     Country filter. Accepts full names (e.g., 'Germany') or ISO-3166 codes ('DE', 'DEU'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``language`` (string) (optional)
     Language filter. Accepts ISO 639-1 codes (e.g., 'en') or full names (e.g., 'English'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``term_override`` (string) (optional)
     Override the default topic seed terms with a custom query string. Defaults internally to 'death'.

   * ``method`` (string) (optional)
     Search strategy: 'keyword' (text only), 'embedding' (vector), or 'hybrid' (blend).

   * ``alpha`` (number) (optional)
     Blend ratio used when method='hybrid' (0=text, 1=embedding).

   * ``top_k`` (integer) (optional)
     Number of candidate documents to retrieve before filtering.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "euhealthinfo_search_deaths",
          "arguments": {
          }
      }
      result = tu.run(query)


**euhealthinfo_search_diabetes_mellitus_epidemiology_registry** (Type: EuHealthTopicSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This tool is designed to search and retrieve datasets related to epidemiological and registry-bas...

.. dropdown:: euhealthinfo_search_diabetes_mellitus_epidemiology_registry tool specification

   **Tool Information:**

   * **Name**: ``euhealthinfo_search_diabetes_mellitus_epidemiology_registry``
   * **Type**: ``EuHealthTopicSearchTool``
   * **Description**: This tool is designed to search and retrieve datasets related to epidemiological and registry-based health data, focusing on diabetes and associated conditions. Users can conduct searches to identify datasets covering prevalence, incidence, and other metrics across varying geographic regions and demographic groups. The tool returns structured datasets enriched with metadata and may provide links to external data sources or downloadable files. It is specialized for accessing curated, health-related information within its defined dataset scope and supports exploration across diverse topics within the diabetes domain. If the user wants to look into the actual data, the 'euhealthinfo_deepdive' tool is helpful.

   **Parameters:**

   * ``limit`` (integer) (optional)
     Maximum number of results to return. Default 25.

   * ``country`` (string) (optional)
     Country filter. Accepts full names (e.g., 'Germany') or ISO-3166 codes ('DE', 'DEU'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``language`` (string) (optional)
     Language filter. Accepts ISO 639-1 codes (e.g., 'en') or full names (e.g., 'English'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``term_override`` (string) (optional)
     Override the default topic seed terms with a custom query string. Defaults internally to 'search diabetes mellitus epidemiology registry'.

   * ``method`` (string) (optional)
     Search strategy: 'keyword' (text only), 'embedding' (vector), or 'hybrid' (blend).

   * ``alpha`` (number) (optional)
     Blend ratio used when method='hybrid' (0=text, 1=embedding).

   * ``top_k`` (integer) (optional)
     Number of candidate documents to retrieve before filtering.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "euhealthinfo_search_diabetes_mellitus_epidemiology_registry",
          "arguments": {
          }
      }
      result = tu.run(query)


**euhealthinfo_search_disability** (Type: EuHealthTopicSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This tool performs searches across multiple dataset repositories to identify datasets related to ...

.. dropdown:: euhealthinfo_search_disability tool specification

   **Tool Information:**

   * **Name**: ``euhealthinfo_search_disability``
   * **Type**: ``EuHealthTopicSearchTool``
   * **Description**: This tool performs searches across multiple dataset repositories to identify datasets related to disabilities, accessibility, functional limitations, and quality of care. It provides links to accessible datasets when available and flags areas requiring further investigation when specific datasets cannot be directly retrieved. If the user wants to look into the actual data, the 'euhealthinfo_deepdive' tool is helpful.

   **Parameters:**

   * ``limit`` (integer) (optional)
     Maximum number of results to return. Default 25.

   * ``country`` (string) (optional)
     Country filter. Accepts full names (e.g., 'Germany') or ISO-3166 codes ('DE', 'DEU'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``language`` (string) (optional)
     Language filter. Accepts ISO 639-1 codes (e.g., 'en') or full names (e.g., 'English'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``term_override`` (string) (optional)
     Override the default topic seed terms with a custom query string. Defaults internally to 'search disability'.

   * ``method`` (string) (optional)
     Search strategy: 'keyword' (text only), 'embedding' (vector), or 'hybrid' (blend).

   * ``alpha`` (number) (optional)
     Blend ratio used when method='hybrid' (0=text, 1=embedding).

   * ``top_k`` (integer) (optional)
     Number of candidate documents to retrieve before filtering.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "euhealthinfo_search_disability",
          "arguments": {
          }
      }
      result = tu.run(query)


**euhealthinfo_search_healthcare_expenditure** (Type: EuHealthTopicSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This tool enables the discovery of healthcare-related datasets focusing on expenditure and spendi...

.. dropdown:: euhealthinfo_search_healthcare_expenditure tool specification

   **Tool Information:**

   * **Name**: ``euhealthinfo_search_healthcare_expenditure``
   * **Type**: ``EuHealthTopicSearchTool``
   * **Description**: This tool enables the discovery of healthcare-related datasets focusing on expenditure and spending trends. It is designed to support users in identifying relevant datasets for comparative analysis across countries or national contexts and provides outputs that indicate dataset availability or absence for specified criteria. If the user wants to look into the actual data, the 'euhealthinfo_deepdive' tool is helpful.

   **Parameters:**

   * ``limit`` (integer) (optional)
     Maximum number of results to return. Default 25.

   * ``country`` (string) (optional)
     Country filter. Accepts full names (e.g., 'Germany') or ISO-3166 codes ('DE', 'DEU'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``language`` (string) (optional)
     Language filter. Accepts ISO 639-1 codes (e.g., 'en') or full names (e.g., 'English'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``term_override`` (string) (optional)
     Override the default topic seed terms with a custom query string. Defaults internally to 'healthcare expenditure'.

   * ``method`` (string) (optional)
     Search strategy: 'keyword' (text only), 'embedding' (vector), or 'hybrid' (blend).

   * ``alpha`` (number) (optional)
     Blend ratio used when method='hybrid' (0=text, 1=embedding).

   * ``top_k`` (integer) (optional)
     Number of candidate documents to retrieve before filtering.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "euhealthinfo_search_healthcare_expenditure",
          "arguments": {
          }
      }
      result = tu.run(query)


**euhealthinfo_search_hospital_in_patient_data** (Type: EuHealthTopicSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This tool is designed to retrieve and explore datasets related to hospital inpatient activity, in...

.. dropdown:: euhealthinfo_search_hospital_in_patient_data tool specification

   **Tool Information:**

   * **Name**: ``euhealthinfo_search_hospital_in_patient_data``
   * **Type**: ``EuHealthTopicSearchTool``
   * **Description**: This tool is designed to retrieve and explore datasets related to hospital inpatient activity, including admissions, discharges, diagnoses, and medical procedures. It aims to provide users with a curated subset of information to identify patterns and trends in inpatient healthcare and enable exploration of broader healthcare contexts. The tool generates results that align with specified search criteria, offering insights into healthcare dynamics across various regions or facility types. If the user wants to look into the actual data, the 'euhealthinfo_deepdive' tool is helpful.

   **Parameters:**

   * ``limit`` (integer) (optional)
     Maximum number of results to return. Default 25.

   * ``country`` (string) (optional)
     Country filter. Accepts full names (e.g., 'Germany') or ISO-3166 codes ('DE', 'DEU'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``language`` (string) (optional)
     Language filter. Accepts ISO 639-1 codes (e.g., 'en') or full names (e.g., 'English'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``term_override`` (string) (optional)
     Override the default topic seed terms with a custom query string. Defaults internally to 'search hospital in patient data'.

   * ``method`` (string) (optional)
     Search strategy: 'keyword' (text only), 'embedding' (vector), or 'hybrid' (blend).

   * ``alpha`` (number) (optional)
     Blend ratio used when method='hybrid' (0=text, 1=embedding).

   * ``top_k`` (integer) (optional)
     Number of candidate documents to retrieve before filtering.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "euhealthinfo_search_hospital_in_patient_data",
          "arguments": {
          }
      }
      result = tu.run(query)


**euhealthinfo_search_infectious_diseases** (Type: EuHealthTopicSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This tool enables users to discover publicly available health-related datasets by searching and a...

.. dropdown:: euhealthinfo_search_infectious_diseases tool specification

   **Tool Information:**

   * **Name**: ``euhealthinfo_search_infectious_diseases``
   * **Type**: ``EuHealthTopicSearchTool``
   * **Description**: This tool enables users to discover publicly available health-related datasets by searching and aggregating data from multiple sources. It uniquely identifies relevant datasets within areas such as epidemiology, disease statistics, and health indicators, providing detailed metadata including access information and thematic classifications. The tool is designed to facilitate exploration of health trends by consolidating resources into a cohesive output tailored to the user's search context. If the user wants to look into the actual data, the 'euhealthinfo_deepdive' tool is helpful.

   **Parameters:**

   * ``limit`` (integer) (optional)
     Maximum number of results to return. Default 25.

   * ``country`` (string) (optional)
     Country filter. Accepts full names (e.g., 'Germany') or ISO-3166 codes ('DE', 'DEU'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``language`` (string) (optional)
     Language filter. Accepts ISO 639-1 codes (e.g., 'en') or full names (e.g., 'English'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``term_override`` (string) (optional)
     Override the default topic seed terms with a custom query string. Defaults internally to 'search infectious diseases'.

   * ``method`` (string) (optional)
     Search strategy: 'keyword' (text only), 'embedding' (vector), or 'hybrid' (blend).

   * ``alpha`` (number) (optional)
     Blend ratio used when method='hybrid' (0=text, 1=embedding).

   * ``top_k`` (integer) (optional)
     Number of candidate documents to retrieve before filtering.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "euhealthinfo_search_infectious_diseases",
          "arguments": {
          }
      }
      result = tu.run(query)


**euhealthinfo_search_key_indicators_registries_surveys** (Type: EuHealthTopicSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This tool identifies and retrieves aggregated datasets that include high-level health indicators ...

.. dropdown:: euhealthinfo_search_key_indicators_registries_surveys tool specification

   **Tool Information:**

   * **Name**: ``euhealthinfo_search_key_indicators_registries_surveys``
   * **Type**: ``EuHealthTopicSearchTool``
   * **Description**: This tool identifies and retrieves aggregated datasets that include high-level health indicators derived from various sources such as registries and surveys. It provides organized metadata and links to these datasets, enabling users to explore public health information across diverse geographic regions and topics. The tool primarily focuses on simplifying access to comprehensive health data summaries suitable for broad analysis and decision-making. If the user wants to look into the actual data, the 'euhealthinfo_deepdive' tool is helpful.

   **Parameters:**

   * ``limit`` (integer) (optional)
     Maximum number of results to return. Default 25.

   * ``country`` (string) (optional)
     Country filter. Accepts full names (e.g., 'Germany') or ISO-3166 codes ('DE', 'DEU'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``language`` (string) (optional)
     Language filter. Accepts ISO 639-1 codes (e.g., 'en') or full names (e.g., 'English'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``term_override`` (string) (optional)
     Override the default topic seed terms with a custom query string. Defaults internally to 'search key indicators registries surveys'.

   * ``method`` (string) (optional)
     Search strategy: 'keyword' (text only), 'embedding' (vector), or 'hybrid' (blend).

   * ``alpha`` (number) (optional)
     Blend ratio used when method='hybrid' (0=text, 1=embedding).

   * ``top_k`` (integer) (optional)
     Number of candidate documents to retrieve before filtering.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "euhealthinfo_search_key_indicators_registries_surveys",
          "arguments": {
          }
      }
      result = tu.run(query)


**euhealthinfo_search_mental_health** (Type: EuHealthTopicSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This tool identifies publicly accessible datasets pertaining to mental health topics. It retrieve...

.. dropdown:: euhealthinfo_search_mental_health tool specification

   **Tool Information:**

   * **Name**: ``euhealthinfo_search_mental_health``
   * **Type**: ``EuHealthTopicSearchTool``
   * **Description**: This tool identifies publicly accessible datasets pertaining to mental health topics. It retrieves datasets from structured studies and aggregated collections, providing insights into mental health, behavioral factors, and related conditions across diverse populations. The tool generates results that align with high-level thematic criteria, enabling informed decision-making for research, policy formation, and intervention strategies. If the user wants to look into the actual data, the 'euhealthinfo_deepdive' tool is helpful.

   **Parameters:**

   * ``limit`` (integer) (optional)
     Maximum number of results to return. Default 25.

   * ``country`` (string) (optional)
     Country filter. Accepts full names (e.g., 'Germany') or ISO-3166 codes ('DE', 'DEU'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``language`` (string) (optional)
     Language filter. Accepts ISO 639-1 codes (e.g., 'en') or full names (e.g., 'English'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``term_override`` (string) (optional)
     Override the default topic seed terms with a custom query string. Defaults internally to 'search mental health'.

   * ``method`` (string) (optional)
     Search strategy: 'keyword' (text only), 'embedding' (vector), or 'hybrid' (blend).

   * ``alpha`` (number) (optional)
     Blend ratio used when method='hybrid' (0=text, 1=embedding).

   * ``top_k`` (integer) (optional)
     Number of candidate documents to retrieve before filtering.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "euhealthinfo_search_mental_health",
          "arguments": {
          }
      }
      result = tu.run(query)


**euhealthinfo_search_obesity** (Type: EuHealthTopicSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This tool facilitates the discovery of datasets related to health topics, specializing in areas s...

.. dropdown:: euhealthinfo_search_obesity tool specification

   **Tool Information:**

   * **Name**: ``euhealthinfo_search_obesity``
   * **Type**: ``EuHealthTopicSearchTool``
   * **Description**: This tool facilitates the discovery of datasets related to health topics, specializing in areas such as obesity, overweight status, BMI, and associated risk factors. Its primary function is to enable users to locate diverse health information resources, focusing on prevalence, trends, and determinants of health conditions and behaviors. If the user wants to look into the actual data, the 'euhealthinfo_deepdive' tool is helpful.

   **Parameters:**

   * ``limit`` (integer) (optional)
     Maximum number of results to return. Default 25.

   * ``country`` (string) (optional)
     Country filter. Accepts full names (e.g., 'Germany') or ISO-3166 codes ('DE', 'DEU'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``language`` (string) (optional)
     Language filter. Accepts ISO 639-1 codes (e.g., 'en') or full names (e.g., 'English'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``term_override`` (string) (optional)
     Override the default topic seed terms with a custom query string. Defaults internally to 'search obesity'.

   * ``method`` (string) (optional)
     Search strategy: 'keyword' (text only), 'embedding' (vector), or 'hybrid' (blend).

   * ``alpha`` (number) (optional)
     Blend ratio used when method='hybrid' (0=text, 1=embedding).

   * ``top_k`` (integer) (optional)
     Number of candidate documents to retrieve before filtering.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "euhealthinfo_search_obesity",
          "arguments": {
          }
      }
      result = tu.run(query)


**euhealthinfo_search_population_health_survey** (Type: EuHealthTopicSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This tool allows users to identify and retrieve datasets from population health surveys conducted...

.. dropdown:: euhealthinfo_search_population_health_survey tool specification

   **Tool Information:**

   * **Name**: ``euhealthinfo_search_population_health_survey``
   * **Type**: ``EuHealthTopicSearchTool``
   * **Description**: This tool allows users to identify and retrieve datasets from population health surveys conducted by international and national organizations. It assists in discovering health-related information, such as survey results and derived indicators, tailored to general thematic interests and geographic contexts. The tool produces a selection of curated survey datasets and relevant access links, offering insights into health trends and research-ready data resources. It ensures its search results are aligned with health-focused global and regional queries, with an emphasis on meaningful and actionable outputs. If the user wants to look into the actual data, the 'euhealthinfo_deepdive' tool is helpful.

   **Parameters:**

   * ``limit`` (integer) (optional)
     Maximum number of results to return. Default 25.

   * ``country`` (string) (optional)
     Country filter. Accepts full names (e.g., 'Germany') or ISO-3166 codes ('DE', 'DEU'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``language`` (string) (optional)
     Language filter. Accepts ISO 639-1 codes (e.g., 'en') or full names (e.g., 'English'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``term_override`` (string) (optional)
     Override the default topic seed terms with a custom query string. Defaults internally to 'search population health survey'.

   * ``method`` (string) (optional)
     Search strategy: 'keyword' (text only), 'embedding' (vector), or 'hybrid' (blend).

   * ``alpha`` (number) (optional)
     Blend ratio used when method='hybrid' (0=text, 1=embedding).

   * ``top_k`` (integer) (optional)
     Number of candidate documents to retrieve before filtering.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "euhealthinfo_search_population_health_survey",
          "arguments": {
          }
      }
      result = tu.run(query)


**euhealthinfo_search_primary_care_workforce** (Type: EuHealthTopicSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This tool is designed to conduct metadata searches for datasets related to the primary-care workf...

.. dropdown:: euhealthinfo_search_primary_care_workforce tool specification

   **Tool Information:**

   * **Name**: ``euhealthinfo_search_primary_care_workforce``
   * **Type**: ``EuHealthTopicSearchTool``
   * **Description**: This tool is designed to conduct metadata searches for datasets related to the primary-care workforce. Its primary purpose is to assist users in identifying data sources that may provide insights into workforce composition and geographic distribution patterns, as well as potentially relevant topics in healthcare professions. Note that the tool requires valid inputs for successful execution and provides either metadata results or error messages indicating invalid parameters when applicable. If the user wants to look into the actual data, the 'euhealthinfo_deepdive' tool is helpful.

   **Parameters:**

   * ``limit`` (integer) (optional)
     Maximum number of results to return. Default 25.

   * ``country`` (string) (optional)
     Country filter. Accepts full names (e.g., 'Germany') or ISO-3166 codes ('DE', 'DEU'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``language`` (string) (optional)
     Language filter. Accepts ISO 639-1 codes (e.g., 'en') or full names (e.g., 'English'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``term_override`` (string) (optional)
     Override the default topic seed terms with a custom query string. Defaults internally to 'search primary care workforce'.

   * ``method`` (string) (optional)
     Search strategy: 'keyword' (text only), 'embedding' (vector), or 'hybrid' (blend).

   * ``alpha`` (number) (optional)
     Blend ratio used when method='hybrid' (0=text, 1=embedding).

   * ``top_k`` (integer) (optional)
     Number of candidate documents to retrieve before filtering.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "euhealthinfo_search_primary_care_workforce",
          "arguments": {
          }
      }
      result = tu.run(query)


**euhealthinfo_search_surveillance** (Type: EuHealthTopicSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The tool facilitates the identification and exploration of health-related datasets across diverse...

.. dropdown:: euhealthinfo_search_surveillance tool specification

   **Tool Information:**

   * **Name**: ``euhealthinfo_search_surveillance``
   * **Type**: ``EuHealthTopicSearchTool``
   * **Description**: The tool facilitates the identification and exploration of health-related datasets across diverse domains. It aggregates information from various sources and provides outputs that help users uncover patterns, trends, and relationships within datasets related to public health, epidemiology, and surveillance activities. It is particularly designed for broad searches and enables access to datasets focused on monitoring health issues globally or regionally. If the user wants to look into the actual data, the 'euhealthinfo_deepdive' tool is helpful.

   **Parameters:**

   * ``limit`` (integer) (optional)
     Maximum number of results to return. Default 25.

   * ``country`` (string) (optional)
     Country filter. Accepts full names (e.g., 'Germany') or ISO-3166 codes ('DE', 'DEU'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``language`` (string) (optional)
     Language filter. Accepts ISO 639-1 codes (e.g., 'en') or full names (e.g., 'English'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``term_override`` (string) (optional)
     Override the default topic seed terms with a custom query string. Defaults internally to 'search surveillance'.

   * ``method`` (string) (optional)
     Search strategy: 'keyword' (text only), 'embedding' (vector), or 'hybrid' (blend).

   * ``alpha`` (number) (optional)
     Blend ratio used when method='hybrid' (0=text, 1=embedding).

   * ``top_k`` (integer) (optional)
     Number of candidate documents to retrieve before filtering.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "euhealthinfo_search_surveillance",
          "arguments": {
          }
      }
      result = tu.run(query)


**euhealthinfo_search_surveillance_mortality_rates** (Type: EuHealthTopicSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The tool identifies and retrieves publicly available sources and systems related to mortality tre...

.. dropdown:: euhealthinfo_search_surveillance_mortality_rates tool specification

   **Tool Information:**

   * **Name**: ``euhealthinfo_search_surveillance_mortality_rates``
   * **Type**: ``EuHealthTopicSearchTool``
   * **Description**: The tool identifies and retrieves publicly available sources and systems related to mortality trends, with a focus on excess mortality and similar patterns. Outputs include details on relevant monitoring systems and resources that provide insights into mortality dynamics within specific geographic or thematic contexts, subject to data availability. If the user wants to look into the actual data, the 'euhealthinfo_deepdive' tool is helpful.

   **Parameters:**

   * ``limit`` (integer) (optional)
     Maximum number of results to return. Default 25.

   * ``country`` (string) (optional)
     Country filter. Accepts full names (e.g., 'Germany') or ISO-3166 codes ('DE', 'DEU'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``language`` (string) (optional)
     Language filter. Accepts ISO 639-1 codes (e.g., 'en') or full names (e.g., 'English'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``term_override`` (string) (optional)
     Override the default topic seed terms with a custom query string. Defaults internally to 'search surveillance mortality rates'.

   * ``method`` (string) (optional)
     Search strategy: 'keyword' (text only), 'embedding' (vector), or 'hybrid' (blend).

   * ``alpha`` (number) (optional)
     Blend ratio used when method='hybrid' (0=text, 1=embedding).

   * ``top_k`` (integer) (optional)
     Number of candidate documents to retrieve before filtering.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "euhealthinfo_search_surveillance_mortality_rates",
          "arguments": {
          }
      }
      result = tu.run(query)


**euhealthinfo_search_vaccination** (Type: EuHealthTopicSearchTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This tool enables users to discover and access datasets related to vaccination and immunization s...

.. dropdown:: euhealthinfo_search_vaccination tool specification

   **Tool Information:**

   * **Name**: ``euhealthinfo_search_vaccination``
   * **Type**: ``EuHealthTopicSearchTool``
   * **Description**: This tool enables users to discover and access datasets related to vaccination and immunization statistics, including global and regional trends and coverage rates. It provides summaries of relevant datasets and facilitates access to comprehensive resources for analyzing health-related data on immunization. If the user wants to look into the actual data, the 'euhealthinfo_deepdive' tool is helpful.

   **Parameters:**

   * ``limit`` (integer) (optional)
     Maximum number of results to return. Default 25.

   * ``country`` (string) (optional)
     Country filter. Accepts full names (e.g., 'Germany') or ISO-3166 codes ('DE', 'DEU'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``language`` (string) (optional)
     Language filter. Accepts ISO 639-1 codes (e.g., 'en') or full names (e.g., 'English'). Case-insensitive; substring/IRI-tail matching allowed.

   * ``term_override`` (string) (optional)
     Override the default topic seed terms with a custom query string. Defaults internally to 'search vaccination'.

   * ``method`` (string) (optional)
     Search strategy: 'keyword' (text only), 'embedding' (vector), or 'hybrid' (blend).

   * ``alpha`` (number) (optional)
     Blend ratio used when method='hybrid' (0=text, 1=embedding).

   * ``top_k`` (integer) (optional)
     Number of candidate documents to retrieve before filtering.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "euhealthinfo_search_vaccination",
          "arguments": {
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
