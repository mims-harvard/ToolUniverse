Machine Learning Tools
======================

**Configuration File**: ``packages/machine_learning_tools.json``
**Tool Type**: Local
**Tools Count**: 20

This page contains all tools defined in the ``machine_learning_tools.json`` configuration file.

Available Tools
---------------

**get_catboost_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about the catboost package. High-performance gradient boosting library

.. dropdown:: get_catboost_info tool specification

   **Tool Information:**

   * **Name**: ``get_catboost_info``
   * **Type**: ``PackageTool``
   * **Description**: Get information about the catboost package. High-performance gradient boosting library

   **Parameters:**

   No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_catboost_info",
          "arguments": {
          }
      }
      result = tu.run(query)


**get_cobrapy_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get comprehensive information about COBRApy – constraint-based metabolic modeling

.. dropdown:: get_cobrapy_info tool specification

   **Tool Information:**

   * **Name**: ``get_cobrapy_info``
   * **Type**: ``PackageTool``
   * **Description**: Get comprehensive information about COBRApy – constraint-based metabolic modeling

   **Parameters:**

   * ``info_type`` (string) (required)
     Type of information to retrieve about COBRApy

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_cobrapy_info",
          "arguments": {
              "info_type": "example_value"
          }
      }
      result = tu.run(query)


**get_deeppurpose_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get comprehensive information about DeepPurpose – deep learning toolkit for drug discovery

.. dropdown:: get_deeppurpose_info tool specification

   **Tool Information:**

   * **Name**: ``get_deeppurpose_info``
   * **Type**: ``PackageTool``
   * **Description**: Get comprehensive information about DeepPurpose – deep learning toolkit for drug discovery

   **Parameters:**

   * ``info_type`` (string) (required)
     Type of information to retrieve about DeepPurpose

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_deeppurpose_info",
          "arguments": {
              "info_type": "example_value"
          }
      }
      result = tu.run(query)


**get_deepxde_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get comprehensive information about DeepXDE – a library for physics-informed neural networks (PIN...

.. dropdown:: get_deepxde_info tool specification

   **Tool Information:**

   * **Name**: ``get_deepxde_info``
   * **Type**: ``PackageTool``
   * **Description**: Get comprehensive information about DeepXDE – a library for physics-informed neural networks (PINNs) solving PDEs and inverse problems.

   **Parameters:**

   * ``include_examples`` (boolean) (required)
     Whether to include usage examples and a quick-start guide

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_deepxde_info",
          "arguments": {
              "include_examples": true
          }
      }
      result = tu.run(query)


**get_faiss_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get comprehensive information about Faiss – efficient similarity search and clustering

.. dropdown:: get_faiss_info tool specification

   **Tool Information:**

   * **Name**: ``get_faiss_info``
   * **Type**: ``PackageTool``
   * **Description**: Get comprehensive information about Faiss – efficient similarity search and clustering

   **Parameters:**

   * ``include_examples`` (boolean) (required)
     Whether to include usage examples and quick start guide

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_faiss_info",
          "arguments": {
              "include_examples": true
          }
      }
      result = tu.run(query)


**get_harmony_pytorch_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get comprehensive information about harmony-pytorch – single-cell data integration

.. dropdown:: get_harmony_pytorch_info tool specification

   **Tool Information:**

   * **Name**: ``get_harmony_pytorch_info``
   * **Type**: ``PackageTool``
   * **Description**: Get comprehensive information about harmony-pytorch – single-cell data integration

   **Parameters:**

   * ``info_type`` (string) (required)
     Type of information to retrieve about harmony-pytorch

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_harmony_pytorch_info",
          "arguments": {
              "info_type": "example_value"
          }
      }
      result = tu.run(query)


**get_hmmlearn_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get comprehensive information about hmmlearn – Hidden Markov Models in Python

.. dropdown:: get_hmmlearn_info tool specification

   **Tool Information:**

   * **Name**: ``get_hmmlearn_info``
   * **Type**: ``PackageTool``
   * **Description**: Get comprehensive information about hmmlearn – Hidden Markov Models in Python

   **Parameters:**

   * ``info_type`` (string) (required)
     Type of information to retrieve about hmmlearn

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_hmmlearn_info",
          "arguments": {
              "info_type": "example_value"
          }
      }
      result = tu.run(query)


**get_imbalanced_learn_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about the imbalanced-learn package. Python toolbox for imbalanced dataset learning

.. dropdown:: get_imbalanced_learn_info tool specification

   **Tool Information:**

   * **Name**: ``get_imbalanced_learn_info``
   * **Type**: ``PackageTool``
   * **Description**: Get information about the imbalanced-learn package. Python toolbox for imbalanced dataset learning

   **Parameters:**

   No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_imbalanced_learn_info",
          "arguments": {
          }
      }
      result = tu.run(query)


**get_lightgbm_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about the lightgbm package. Fast gradient boosting framework

.. dropdown:: get_lightgbm_info tool specification

   **Tool Information:**

   * **Name**: ``get_lightgbm_info``
   * **Type**: ``PackageTool``
   * **Description**: Get information about the lightgbm package. Fast gradient boosting framework

   **Parameters:**

   No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_lightgbm_info",
          "arguments": {
          }
      }
      result = tu.run(query)


**get_optuna_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about the optuna package. Hyperparameter optimization framework

.. dropdown:: get_optuna_info tool specification

   **Tool Information:**

   * **Name**: ``get_optuna_info``
   * **Type**: ``PackageTool``
   * **Description**: Get information about the optuna package. Hyperparameter optimization framework

   **Parameters:**

   No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_optuna_info",
          "arguments": {
          }
      }
      result = tu.run(query)


**get_pymzml_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get comprehensive information about pymzML – mzML file parser for mass spectrometry

.. dropdown:: get_pymzml_info tool specification

   **Tool Information:**

   * **Name**: ``get_pymzml_info``
   * **Type**: ``PackageTool``
   * **Description**: Get comprehensive information about pymzML – mzML file parser for mass spectrometry

   **Parameters:**

   * ``info_type`` (string) (required)
     Type of information to retrieve about pymzML

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_pymzml_info",
          "arguments": {
              "info_type": "example_value"
          }
      }
      result = tu.run(query)


**get_python_libsbml_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get comprehensive information about python-libsbml – SBML (Systems Biology Markup Language) support

.. dropdown:: get_python_libsbml_info tool specification

   **Tool Information:**

   * **Name**: ``get_python_libsbml_info``
   * **Type**: ``PackageTool``
   * **Description**: Get comprehensive information about python-libsbml – SBML (Systems Biology Markup Language) support

   **Parameters:**

   * ``info_type`` (string) (required)
     Type of information to retrieve about python-libsbml

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_python_libsbml_info",
          "arguments": {
              "info_type": "example_value"
          }
      }
      result = tu.run(query)


**get_pytorch_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get comprehensive information about PyTorch – an open source machine learning framework

.. dropdown:: get_pytorch_info tool specification

   **Tool Information:**

   * **Name**: ``get_pytorch_info``
   * **Type**: ``PackageTool``
   * **Description**: Get comprehensive information about PyTorch – an open source machine learning framework

   **Parameters:**

   * ``include_examples`` (boolean) (required)
     Whether to include usage examples and quick start guide

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_pytorch_info",
          "arguments": {
              "include_examples": true
          }
      }
      result = tu.run(query)


**get_schnetpack_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get comprehensive information about SchNetPack – a deep-learning toolbox for molecules and materi...

.. dropdown:: get_schnetpack_info tool specification

   **Tool Information:**

   * **Name**: ``get_schnetpack_info``
   * **Type**: ``PackageTool``
   * **Description**: Get comprehensive information about SchNetPack – a deep-learning toolbox for molecules and materials built on PyTorch.

   **Parameters:**

   * ``include_examples`` (boolean) (required)
     Whether to include usage examples and a quick-start guide

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_schnetpack_info",
          "arguments": {
              "include_examples": true
          }
      }
      result = tu.run(query)


**get_scikit_learn_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get comprehensive information about scikit-learn – simple and efficient tools for predictive data...

.. dropdown:: get_scikit_learn_info tool specification

   **Tool Information:**

   * **Name**: ``get_scikit_learn_info``
   * **Type**: ``PackageTool``
   * **Description**: Get comprehensive information about scikit-learn – simple and efficient tools for predictive data analysis

   **Parameters:**

   * ``include_examples`` (boolean) (required)
     Whether to include usage examples and quick start guide

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_scikit_learn_info",
          "arguments": {
              "include_examples": true
          }
      }
      result = tu.run(query)


**get_skopt_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about the skopt package. Scikit-Optimize: sequential model-based optimization

.. dropdown:: get_skopt_info tool specification

   **Tool Information:**

   * **Name**: ``get_skopt_info``
   * **Type**: ``PackageTool``
   * **Description**: Get information about the skopt package. Scikit-Optimize: sequential model-based optimization

   **Parameters:**

   No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_skopt_info",
          "arguments": {
          }
      }
      result = tu.run(query)


**get_statsmodels_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get comprehensive information about statsmodels – statistical modeling and econometrics

.. dropdown:: get_statsmodels_info tool specification

   **Tool Information:**

   * **Name**: ``get_statsmodels_info``
   * **Type**: ``PackageTool``
   * **Description**: Get comprehensive information about statsmodels – statistical modeling and econometrics

   **Parameters:**

   * ``include_examples`` (boolean) (required)
     Whether to include usage examples and quick start guide

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_statsmodels_info",
          "arguments": {
              "include_examples": true
          }
      }
      result = tu.run(query)


**get_torch_geometric_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get comprehensive information about PyTorch Geometric – a high-performance library for graph neur...

.. dropdown:: get_torch_geometric_info tool specification

   **Tool Information:**

   * **Name**: ``get_torch_geometric_info``
   * **Type**: ``PackageTool``
   * **Description**: Get comprehensive information about PyTorch Geometric – a high-performance library for graph neural networks widely used in molecular and materials science.

   **Parameters:**

   * ``include_examples`` (boolean) (required)
     Whether to include usage examples and quick start guide

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_torch_geometric_info",
          "arguments": {
              "include_examples": true
          }
      }
      result = tu.run(query)


**get_umap_learn_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get comprehensive information about UMAP-learn – dimensionality reduction technique

.. dropdown:: get_umap_learn_info tool specification

   **Tool Information:**

   * **Name**: ``get_umap_learn_info``
   * **Type**: ``PackageTool``
   * **Description**: Get comprehensive information about UMAP-learn – dimensionality reduction technique

   **Parameters:**

   * ``include_examples`` (boolean) (required)
     Whether to include usage examples and quick start guide

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_umap_learn_info",
          "arguments": {
              "include_examples": true
          }
      }
      result = tu.run(query)


**get_xgboost_info** (Type: PackageTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Get information about the xgboost package. Optimized gradient boosting framework

.. dropdown:: get_xgboost_info tool specification

   **Tool Information:**

   * **Name**: ``get_xgboost_info``
   * **Type**: ``PackageTool``
   * **Description**: Get information about the xgboost package. Optimized gradient boosting framework

   **Parameters:**

   No parameters required.

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "get_xgboost_info",
          "arguments": {
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
