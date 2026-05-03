File Download Tools
===================

**Configuration File**: ``file_download_tools.json``
**Tool Type**: Local
**Tools Count**: 3

This page contains all tools defined in the ``file_download_tools.json`` configuration file.

Available Tools
---------------

**download_binary_file** (Type: BinaryDownloadTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Download binary files (images, videos, executables) with chunked streaming for better memory mana...

.. dropdown:: download_binary_file tool specification

   **Tool Information:**

   * **Name**: ``download_binary_file``
   * **Type**: ``BinaryDownloadTool``
   * **Description**: Download binary files (images, videos, executables) with chunked streaming for better memory management. Optimized for large files.

   **Parameters:**

   * ``url`` (string) (required)
     HTTP or HTTPS URL to download from

   * ``output_path`` (string) (required)
     Full path where to save the binary file (e.g., /tmp/image.jpg or C:\Users\Downloads\video.mp4)

   * ``chunk_size`` (integer) (optional)
     Download chunk size in bytes (default: 1MB for binary files)

   * ``timeout`` (integer) (optional)
     Request timeout in seconds

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "download_binary_file",
          "arguments": {
              "url": "example_value",
              "output_path": "example_value"
          }
      }
      result = tu.run(query)


**download_file** (Type: FileDownloadTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Download files from HTTP/HTTPS URLs with cross-platform support (Windows, Mac, Linux). Similar to...

.. dropdown:: download_file tool specification

   **Tool Information:**

   * **Name**: ``download_file``
   * **Type**: ``FileDownloadTool``
   * **Description**: Download files from HTTP/HTTPS URLs with cross-platform support (Windows, Mac, Linux). Similar to curl but platform-independent. Can save to specified path or temporary directory.

   **Parameters:**

   * ``url`` (string) (required)
     HTTP or HTTPS URL to download from (e.g., https://example.com/file.txt)

   * ``output_path`` (string) (optional)
     Optional path to save the file. If not specified, file will be saved to system temp directory.

   * ``timeout`` (integer) (optional)
     Request timeout in seconds

   * ``return_content`` (boolean) (optional)
     If true, return file content as text instead of saving to disk (default: false)

   * ``chunk_size`` (integer) (optional)
     Download chunk size in bytes (default: 8192)

   * ``follow_redirects`` (boolean) (optional)
     Follow HTTP redirects (default: true)

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "download_file",
          "arguments": {
              "url": "example_value"
          }
      }
      result = tu.run(query)


**download_text_content** (Type: TextDownloadTool)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Download and return text content from URLs. Optimized for text files with automatic encoding dete...

.. dropdown:: download_text_content tool specification

   **Tool Information:**

   * **Name**: ``download_text_content``
   * **Type**: ``TextDownloadTool``
   * **Description**: Download and return text content from URLs. Optimized for text files with automatic encoding detection.

   **Parameters:**

   * ``url`` (string) (required)
     HTTP or HTTPS URL to download text from

   * ``encoding`` (string) (optional)
     Text encoding (e.g., utf-8, latin1). Auto-detected if not specified.

   * ``timeout`` (integer) (optional)
     Request timeout in seconds

   **Example Usage:**

   .. code-block:: python

      query = {
          "name": "download_text_content",
          "arguments": {
              "url": "example_value"
          }
      }
      result = tu.run(query)


Navigation
----------

* :doc:`tools_config_index` - Back to Tools Overview
* :doc:`../guide/loading_tools` - Loading Local Tools
