SIMBAD Tools
============

**Configuration File**: ``simbad_tools.json``
**Tool Type**: Local
**Tools Count**: 2

This page contains all tools for querying the SIMBAD astronomical database.

Overview
--------

SIMBAD (Set of Identifications, Measurements, and Bibliography for Astronomical Data) is a comprehensive astronomical database maintained by the Centre de Données astronomiques de Strasbourg (CDS). It provides information on millions of astronomical objects beyond the Solar System, including stars, galaxies, nebulae, and other celestial bodies.

These tools provide access to SIMBAD's extensive collection of:

* Object identifications and cross-references
* Coordinates and proper motions
* Spectral types and classifications
* Photometric measurements
* Bibliographic references
* Observational data

Available Tools
---------------

**SIMBAD_query_object** (Type: SIMBADTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Query the SIMBAD astronomical database for information about celestial objects. Supports queries by object name, coordinates, or identifier patterns.

.. dropdown:: SIMBAD_query_object tool specification

   **Tool Information:**

   * **Name**: ``SIMBAD_query_object``
   * **Type**: ``SIMBADTool``
   * **Description**: Query the SIMBAD astronomical database for information about celestial objects. Supports queries by object name, coordinates, or identifier. SIMBAD contains data on millions of astronomical objects including stars, galaxies, and other celestial bodies.

   **Parameters:**

   * ``query_type`` (string) (optional)
     Type of query to perform. Options: 'object_name' (search by name), 'coordinates' (search by position), 'identifier' (search by identifier pattern). Default: 'object_name'

   * ``object_name`` (string) (conditional)
     Name of the astronomical object (e.g., 'M31', 'Sirius', 'NGC 1068'). Required when query_type='object_name'

   * ``ra`` (number) (conditional)
     Right Ascension in degrees (0-360). Required when query_type='coordinates'

   * ``dec`` (number) (conditional)
     Declination in degrees (-90 to +90). Required when query_type='coordinates'

   * ``radius`` (number) (optional)
     Search radius in arcminutes for coordinate queries. Default: 1.0

   * ``identifier`` (string) (conditional)
     Identifier pattern with wildcards (e.g., 'HD *', 'NGC 10*'). Required when query_type='identifier'

   * ``output_format`` (string) (optional)
     Level of detail in output. Options: 'basic' (ID, coordinates, type), 'detailed' (includes spectral type and flux), 'full' (all available data). Default: 'basic'

   * ``max_results`` (integer) (optional)
     Maximum number of results to return for coordinate or identifier queries. Default: 10

   **Return Schema:**

   Returns a dictionary with the following structure:

   * ``success`` (boolean): Whether the query was successful
   * ``query`` (string): Description of the query executed
   * ``count`` (integer): Number of results returned
   * ``results`` (array): Array of astronomical objects, each containing:
     
     - ``main_id`` (string): Primary identifier for the object
     - ``coordinates`` (string): Coordinates in ICRS format
     - ``object_type`` (string): Type of astronomical object
     - ``spectral_type`` (string): Spectral type (if available and format is detailed/full)
     - ``flux`` (string): Flux measurements (if available and format is detailed/full)

   * ``error`` (string): Error message if query failed

   **Example Usage:**

   Query by object name:

   .. code-block:: python

      from tooluniverse import ToolUniverse

      tu = ToolUniverse()
      tu.load_tools()

      # Query the Andromeda Galaxy
      query = {
          "name": "SIMBAD_query_object",
          "arguments": {
              "query_type": "object_name",
              "object_name": "M31",
              "output_format": "detailed"
          }
      }
      result = tu.run_one_function(query)
      print(result)

   Query by coordinates:

   .. code-block:: python

      # Search for objects near specific coordinates
      query = {
          "name": "SIMBAD_query_object",
          "arguments": {
              "query_type": "coordinates",
              "ra": 10.68458,
              "dec": 41.26917,
              "radius": 2.0,
              "max_results": 5
          }
      }
      result = tu.run_one_function(query)

   Query by identifier pattern:

   .. code-block:: python

      # Find all NGC objects starting with "10"
      query = {
          "name": "SIMBAD_query_object",
          "arguments": {
              "query_type": "identifier",
              "identifier": "NGC 10*",
              "max_results": 10
          }
      }
      result = tu.run_one_function(query)


**SIMBAD_advanced_query** (Type: SIMBADAdvancedTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute advanced ADQL (Astronomical Data Query Language) queries on SIMBAD using TAP (Table Access Protocol). Allows complex database queries with SQL-like syntax.

.. dropdown:: SIMBAD_advanced_query tool specification

   **Tool Information:**

   * **Name**: ``SIMBAD_advanced_query``
   * **Type**: ``SIMBADAdvancedTool``
   * **Description**: Execute advanced ADQL (Astronomical Data Query Language) queries on SIMBAD using TAP (Table Access Protocol). Allows complex database queries with SQL-like syntax for sophisticated astronomical data searches. Use this for queries that require joins, filtering, or complex conditions.

   **Parameters:**

   * ``adql_query`` (string) (required)
     ADQL query string. Example: 'SELECT TOP 10 main_id, ra, dec, otype FROM basic WHERE otype='Star' AND ra BETWEEN 0 AND 10'

   * ``max_results`` (integer) (optional)
     Maximum number of results to return. Default: 100

   * ``format`` (string) (optional)
     Output format. Options: 'json' or 'votable'. Default: 'json'

   **Return Schema:**

   Returns a dictionary with:

   * ``success`` (boolean): Whether the query was successful
   * ``query`` (string): The ADQL query that was executed
   * ``results``: Query results in requested format (JSON object or VOTable XML string)
   * ``error`` (string): Error message if query failed

   **Example Usage:**

   Basic ADQL query:

   .. code-block:: python

      from tooluniverse import ToolUniverse

      tu = ToolUniverse()
      tu.load_tools()

      # Query for nearby stars
      query = {
          "name": "SIMBAD_advanced_query",
          "arguments": {
              "adql_query": "SELECT TOP 5 main_id, ra, dec, otype FROM basic WHERE otype='Star*' AND ra BETWEEN 0 AND 10",
              "max_results": 5,
              "format": "json"
          }
      }
      result = tu.run_one_function(query)

   Query with specific object:

   .. code-block:: python

      # Get proper motion data for Sirius
      query = {
          "name": "SIMBAD_advanced_query",
          "arguments": {
              "adql_query": "SELECT main_id, pmra, pmdec FROM basic WHERE main_id='Sirius'",
              "format": "json"
          }
      }
      result = tu.run_one_function(query)


Common Use Cases
----------------

Finding Object Information
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Get basic information about a star
   result = tu.run_one_function({
       "name": "SIMBAD_query_object",
       "arguments": {
           "object_name": "Betelgeuse",
           "output_format": "detailed"
       }
   })

Coordinate-Based Searches
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Find all objects within 5 arcminutes of a position
   result = tu.run_one_function({
       "name": "SIMBAD_query_object",
       "arguments": {
           "query_type": "coordinates",
           "ra": 83.6333,
           "dec": -5.3917,
           "radius": 5.0,
           "max_results": 20
       }
   })

Complex ADQL Queries
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Advanced query for specific object types in a region
   result = tu.run_one_function({
       "name": "SIMBAD_advanced_query",
       "arguments": {
           "adql_query": """
               SELECT main_id, ra, dec, otype, pmra, pmdec 
               FROM basic 
               WHERE otype LIKE 'Galaxy%' 
               AND ra BETWEEN 10 AND 20 
               AND dec BETWEEN -10 AND 10
               ORDER BY main_id
           """,
           "max_results": 50
       }
   })

Tips and Best Practices
------------------------

1. **Object Names**: SIMBAD recognizes various object naming conventions (Messier, NGC, HD, etc.). You can use common names or catalog identifiers.

2. **Coordinate Searches**: When searching by coordinates, start with a smaller radius and increase if needed to avoid too many results.

3. **Output Formats**: 
   - Use 'basic' format for quick lookups
   - Use 'detailed' for additional information like spectral types
   - Use 'full' when you need comprehensive data

4. **ADQL Queries**: 
   - The 'basic' table is the main table for most queries
   - Use 'TOP N' to limit results in ADQL queries
   - Wildcards can be used with LIKE operator (e.g., ``otype LIKE 'Star*'``)

5. **Error Handling**: Always check for the 'error' field in results, especially for coordinate searches that may return no objects.

Limitations
-----------

* **Rate Limits**: Be mindful of query frequency when making automated requests
* **Timeout**: Complex TAP queries may timeout; consider breaking them into smaller queries
* **Object Names**: Some objects may have multiple identifiers; SIMBAD returns the primary identifier

References
----------

* `SIMBAD Database <http://simbad.cds.unistra.fr/>`_
* `SIMBAD User Guide <http://simbad.cds.unistra.fr/guide/>`_
* `TAP Protocol Documentation <http://www.ivoa.net/documents/TAP/>`_
* `ADQL Documentation <http://www.ivoa.net/documents/ADQL/>`_

Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
* :doc:`physics_astronomy_tools` - Related Astronomy Tools
