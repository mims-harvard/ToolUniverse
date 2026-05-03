"""
DepMap Gene Correlation Tool - MCP Server

This module provides an MCP (Model Context Protocol) server for analyzing gene-gene
correlations from the DepMap (Dependency Map) dataset. The tool processes CRISPR
knockout screening data from cancer cell lines to identify genetic dependencies
and synthetic lethal relationships.

The DepMap dataset contains systematic CRISPR-Cas9 knockout screens across over
1,000 cancer cell lines, providing insights into essential genes and genetic
interactions that can inform therapeutic target discovery and drug development.
"""

import numpy as np
import os
import h5py
import asyncio
import uuid
from typing import Dict, Optional
from fastmcp import FastMCP

# Initialize MCP Server for DepMap gene correlation analysis
server = FastMCP("DepMap Gene Correlation SMCP Server")


class DepmapCorrelationTool:
    """
    Comprehensive tool for analyzing gene-gene correlations from DepMap CRISPR knockout data.

    This class provides functionality to:
    - Load and index large-scale DepMap correlation matrices
    - Perform efficient gene-gene correlation lookups
    - Access statistical significance metrics (p-values, adjusted p-values)
    - Handle both dense and sparse matrix formats for scalability

    The tool processes DepMap 24Q2 data containing CRISPR knockout effects across
    1,320+ cancer cell lines, enabling identification of genetic dependencies,
    synthetic lethal relationships, and co-essential gene pairs.

    Supports multiple data formats:
    - Dense matrices (.npy files) for smaller datasets
    - Sparse matrices (HDF5) for memory-efficient large-scale analysis
    """

    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize the DepMap correlation tool by loading preprocessed correlation data.

        Args:
            data_dir (str, optional): Path to directory containing DepMap correlation matrices.
                                    If None, uses DEPMAP_DATA_PATH/depmap_24q2.

        Raises:
            FileNotFoundError: If the specified data directory or required files cannot be found.
            Exception: If data loading fails due to format issues or corruption.
        """
        # Construct data directory path
        if data_dir is None:
            depmap_data_path = os.getenv("DEPMAP_DATA_PATH", "")
            self.data_dir = os.path.join(depmap_data_path, "depmap_24q2")
        else:
            self.data_dir = data_dir

        # Validate data directory exists
        if not os.path.exists(self.data_dir):
            raise FileNotFoundError(
                f"DepMap data directory not found at {self.data_dir}. Please check your DEPMAP_DATA_PATH."
            )

        # Load DepMap correlation data and gene indices
        print(f"Initializing DepMap correlation tool from data: {self.data_dir}...")
        self._load_gene_index()
        self._load_correlation_data()
        print(
            f"DepMap tool initialized successfully (loaded correlation data for {self.num_genes:,} genes)."
        )

    def _load_gene_index(self):
        """
        Load gene symbol index and create efficient lookup mapping.

        This method loads the gene names from either a preprocessed numpy array
        or a text file, then creates a dictionary mapping for O(1) gene lookups.
        The gene index is essential for translating gene symbols to matrix indices.

        Raises:
            FileNotFoundError: If neither gene index file format is found.
        """
        try:
            # Try loading preprocessed gene index array first (faster)
            gene_idx_path = os.path.join(self.data_dir, "gene_idx_array.npy")
            if os.path.exists(gene_idx_path):
                self.gene_names = np.load(
                    gene_idx_path, allow_pickle=True, mmap_mode="r"
                )
            else:
                # Fallback to text file format
                gene_names_path = os.path.join(self.data_dir, "gene_names.txt")
                with open(gene_names_path, "r", encoding="utf-8") as f:
                    self.gene_names = np.array([line.strip() for line in f])

            # Create bidirectional mapping for efficient gene symbol lookups
            self.gene_to_idx = {gene: idx for idx, gene in enumerate(self.gene_names)}
            self.num_genes = len(self.gene_names)

        except FileNotFoundError:
            raise FileNotFoundError(
                f"Gene names file not found in {self.data_dir}. Expected 'gene_idx_array.npy' or 'gene_names.txt'."
            )

    def _load_correlation_data(self):
        """
        Load correlation matrices and statistical data in optimal format.

        This method automatically detects and loads correlation data from either:
        1. Dense numpy matrices (.npy files) - faster for smaller datasets
        2. Sparse HDF5 format - memory-efficient for large-scale data

        The method also checks for adjusted p-values (FDR correction) availability
        and configures the appropriate data access methods.

        Raises:
            FileNotFoundError: If no correlation data files are found in the expected formats.
        """
        # Check for dense matrix format first
        corr_matrix_path = os.path.join(self.data_dir, "corr_matrix.npy")
        p_val_matrix_path = os.path.join(self.data_dir, "p_val_matrix.npy")

        if os.path.exists(corr_matrix_path) and os.path.exists(p_val_matrix_path):
            # Load dense matrices with memory mapping for efficiency
            self.corr_matrix = np.load(corr_matrix_path, mmap_mode="r")
            self.p_val_matrix = np.load(p_val_matrix_path, mmap_mode="r")
            self.format = "dense"

            # Check for FDR-adjusted p-values
            p_adj_matrix_path = os.path.join(self.data_dir, "p_adj_matrix.npy")
            if os.path.exists(p_adj_matrix_path):
                self.p_adj_matrix = np.load(p_adj_matrix_path, mmap_mode="r")
                self.has_adj_p = True
            else:
                self.has_adj_p = False
        else:
            # Fallback to sparse HDF5 format for large datasets
            h5_path = os.path.join(self.data_dir, "gene_correlations.h5")
            if not os.path.exists(h5_path):
                raise FileNotFoundError(
                    f"No correlation data found in {self.data_dir}. Expected either dense (.npy) or sparse (.h5) format."
                )

            self.h5_file = h5py.File(h5_path, "r")
            self.format = "sparse"
            self.has_adj_p = "p_adj" in self.h5_file

    def get_correlation(self, gene_a: str, gene_b: str) -> Dict[str, float]:
        """
        Retrieve correlation coefficient and statistical significance between two genes.

        This method performs efficient lookup of gene-gene correlations from DepMap
        CRISPR knockout data, providing both correlation strength and statistical
        significance metrics for genetic interaction analysis.

        Args:
            gene_a (str): First gene symbol (e.g., 'BRAF', 'TP53'). Must be present in dataset.
            gene_b (str): Second gene symbol (e.g., 'MAPK1', 'MDM2'). Must be present in dataset.

        Returns
            Dict[str, float]: Dictionary containing correlation analysis results:
                - 'correlation': Pearson correlation coefficient (-1.0 to 1.0)
                - 'p_value': Statistical significance of correlation
                - 'adjusted_p_value': FDR-corrected p-value (if available)

        Raises:
            KeyError: If either gene symbol is not found in the correlation matrix.
        """
        # Validate gene symbols exist in dataset
        if gene_a not in self.gene_to_idx:
            raise KeyError(
                f"Gene '{gene_a}' not available in the DepMap correlation matrix. Check gene symbol spelling."
            )
        if gene_b not in self.gene_to_idx:
            raise KeyError(
                f"Gene '{gene_b}' not available in the DepMap correlation matrix. Check gene symbol spelling."
            )

        # Convert gene symbols to matrix indices
        idx_a = self.gene_to_idx[gene_a]
        idx_b = self.gene_to_idx[gene_b]

        if self.format == "dense":
            # Direct matrix access for dense format
            result = {
                "correlation": float(self.corr_matrix[idx_a, idx_b]),
                "p_value": float(self.p_val_matrix[idx_a, idx_b]),
            }
            if self.has_adj_p:
                result["adjusted_p_value"] = float(self.p_adj_matrix[idx_a, idx_b])
        else:  # sparse format

            def get_csr_value(group, row, col):
                """Extract value from compressed sparse row matrix in HDF5 format."""
                indptr, indices, data = (
                    group["indptr"][:],
                    group["indices"][:],
                    group["data"][:],
                )
                for i in range(indptr[row], indptr[row + 1]):
                    if indices[i] == col:
                        return float(data[i])
                return 0.0  # Return 0 for missing values in sparse matrix

            # Extract correlation data from sparse HDF5 format
            result = {
                "correlation": get_csr_value(self.h5_file["corr"], idx_a, idx_b),
                "p_value": get_csr_value(self.h5_file["p_val"], idx_a, idx_b),
            }
            if self.has_adj_p:
                result["adjusted_p_value"] = get_csr_value(
                    self.h5_file["p_adj"], idx_a, idx_b
                )

        return result

    def __del__(self):
        """
        Clean up resources when the tool instance is destroyed.

        Ensures proper closure of HDF5 file handles to prevent resource leaks
        when using sparse matrix format.
        """
        if (
            hasattr(self, "format")
            and self.format == "sparse"
            and hasattr(self, "h5_file")
        ):
            self.h5_file.close()


@server.tool()
async def compute_depmap24q2_gene_correlations(
    gene_a: str, gene_b: str, data_dir: Optional[str] = None
):
    """
    MCP Tool: Analyzes gene-gene correlations from DepMap CRISPR knockout screening data.

    This tool validates genetic interactions using empirical cell viability data from
    1,320+ cancer cell lines in the DepMap 24Q2 dataset. It determines if two genes
    have correlated knockout effects, providing insights into genetic dependencies
    and synthetic lethal relationships.

    Biological Interpretation:
    - Positive correlations indicate co-dependency (genes with shared essential functions)
    - Negative correlations suggest synthetic lethality (compensatory relationships)
    - Strong correlations (|r| > 0.5) with statistical significance (adj_p < 0.05)
      provide robust evidence for therapeutic targeting opportunities

    Clinical Applications:
    - Prioritize gene pairs for experimental validation
    - Inform combination therapy development strategies
    - Guide functional genomics studies
    - Translate pathway predictions into clinically-actionable insights
    - Identify potential drug targets and resistance mechanisms

    Data Source:
    - DepMap 24Q2 release containing CRISPR-Cas9 knockout screens
    - Over 1,320 well-characterized cancer cell lines
    - Standardized gene effect scores (CERES algorithm)
    - Multiple statistical correction methods applied

    Args:
        gene_a (str): First gene symbol for correlation analysis (e.g., 'BRAF', 'TP53').
                     Must use standard HUGO gene nomenclature.
        gene_b (str): Second gene symbol for correlation analysis (e.g., 'MAPK1', 'MDM2').
                     Must use standard HUGO gene nomenclature.

    Returns
        dict: Comprehensive correlation analysis results containing:
            - 'correlation_data' (dict): Statistical measures including:
                * 'correlation': Pearson correlation coefficient (-1.0 to 1.0)
                * 'p_value': Statistical significance of correlation
                * 'adjusted_p_value': FDR-corrected p-value (when available)
            - 'interpretation' (dict): Biological and statistical context including:
                * 'strength': Descriptive correlation strength assessment
                * 'significance': Statistical significance interpretation
                * 'direction': Relationship type (similar vs opposing effects)
                * 'summary': Comprehensive analysis summary
            - 'context_info' (list): Detailed analysis messages and metadata
            - 'error' (str, optional): Error description if analysis failed

    Example Usage:
        # Analyze BRAF-MAPK1 interaction (oncogenic pathway)
        result = await compute_depmap24q2_gene_correlations("BRAF", "MAPK1")

        # Check synthetic lethality between DNA repair genes
        result = await compute_depmap24q2_gene_correlations("BRCA1", "PARP1")
    """
    # Generate unique request ID for tracking and logging
    request_id = str(uuid.uuid4())[:8]
    print(
        f"[{request_id}] Received DepMap gene correlation analysis request: {gene_a} vs {gene_b}"
    )

    context_info = []

    # Initialize global DepMap tool instance for MCP server
    # This instance will be used by the MCP tool function to serve correlation queries
    try:
        depmap_tool = DepmapCorrelationTool(data_dir=data_dir)
        print("DepMap Correlation tool instance created and ready for MCP server")
    except Exception as e:
        print(f"Error creating DepMap Correlation tool: {str(e)}")
        print(
            "Please ensure DEPMAP_DATA_PATH is correctly set and correlation data exists."
        )
        raise e

    try:
        # Brief async pause to allow for proper request handling
        await asyncio.sleep(0.1)

        # Input validation and standardization
        gene_a_std = gene_a.upper().strip()
        gene_b_std = gene_b.upper().strip()

        if not gene_a_std or not gene_b_std:
            raise ValueError(
                "Gene symbols cannot be empty. Please provide valid HUGO gene symbols."
            )

        if gene_a_std == gene_b_std:
            context_info.append(
                f"Note: Analyzing self-correlation for gene {gene_a_std} (diagonal element)."
            )

        print(
            f"[{request_id}] Processing correlation analysis for standardized genes: {gene_a_std} vs {gene_b_std}"
        )

        # Execute DepMap correlation lookup
        corr_data = depmap_tool.get_correlation(gene_a_std, gene_b_std)
        correlation = corr_data["correlation"]
        p_value = corr_data["p_value"]
        adj_p_value = corr_data.get("adjusted_p_value")

        context_info.append(
            "Successfully retrieved correlation data from DepMap 24Q2 dataset."
        )
        context_info.append(
            "Analysis based on CRISPR knockout effects across 1,320+ cancer cell lines."
        )

        # Statistical and biological interpretation functions
        def _interpret_strength(c):
            """Classify correlation strength based on absolute value."""
            abs_c = abs(c)
            if abs_c >= 0.8:
                return "very strong"
            if abs_c >= 0.6:
                return "strong"
            if abs_c >= 0.4:
                return "moderate"
            if abs_c >= 0.2:
                return "weak"
            return "negligible"

        def _interpret_significance(p, adj_p):
            """Determine statistical significance with appropriate correction."""
            if adj_p is not None and adj_p <= 0.05:
                return "significant (FDR corrected)"
            if adj_p is not None and adj_p <= 0.1:
                return "marginally significant (FDR corrected)"
            if p <= 0.05:
                return "significant (uncorrected)"
            if p <= 0.1:
                return "marginally significant (uncorrected)"
            return "not statistically significant"

        def _interpret_biological_relationship(corr, strength):
            """Provide biological context for correlation direction and strength."""
            if strength == "negligible":
                return "independent knockout effects"
            elif corr > 0:
                return "co-dependent relationship (shared essential functions)"
            else:
                return "synthetic lethal relationship (compensatory functions)"

        # Generate comprehensive interpretation
        strength = _interpret_strength(correlation)
        significance = _interpret_significance(p_value, adj_p_value)
        direction = "similar" if correlation > 0 else "opposing"
        biological_relationship = _interpret_biological_relationship(
            correlation, strength
        )

        interpretation = {
            "strength": strength,
            "significance": significance,
            "direction": direction,
            "biological_relationship": biological_relationship,
            "summary": f"DepMap analysis reveals a {strength}, {direction} correlation (r={correlation:.3f}) in knockout effects between {gene_a_std} and {gene_b_std}, suggesting {biological_relationship}. This finding is {significance}.",
        }

        # Log successful completion with key metrics
        print(
            f"[{request_id}] DepMap correlation analysis completed: r={correlation:.3f}, p={p_value:.2e}"
        )

        return {
            "correlation_data": corr_data,
            "interpretation": interpretation,
            "context_info": context_info,
        }

    except (KeyError, ValueError, FileNotFoundError) as e:
        error_message = f"DepMap correlation analysis validation error: {str(e)}"
        print(f"[{request_id}] {error_message}")
        return {
            "error": error_message,
            "context_info": context_info
            + ["Please verify gene symbols and data availability."],
        }
    except Exception as e:
        error_message = f"Unexpected error during DepMap correlation analysis: {str(e)}"
        print(f"[{request_id}] {error_message}")
        return {
            "error": error_message,
            "context_info": context_info
            + ["Internal server error occurred during analysis."],
        }


if __name__ == "__main__":
    print("Starting MCP server for DepMap Gene Correlation Analysis Tool...")
    print("Dataset: DepMap 24Q2 CRISPR knockout screening data")
    print("Coverage: 1,320+ cancer cell lines with genetic dependency profiles")
    print("Application: Genetic interaction analysis and synthetic lethality discovery")
    print("Server: FastMCP with streamable HTTP transport")
    print("Port: 7002 (configured to avoid conflicts with other biomedical tools)")

    # Launch the MCP server with DepMap correlation analysis capabilities
    server.run(
        transport="streamable-http", host="0.0.0.0", port=7002, stateless_http=True
    )
