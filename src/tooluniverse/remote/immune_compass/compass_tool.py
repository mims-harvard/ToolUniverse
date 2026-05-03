"""
COMPASS Prediction Tool - MCP Server

This module provides an MCP (Model Context Protocol) server for running immune checkpoint
inhibitor (ICI) response predictions using the COMPASS (COMprehensive Pathway Analysis
for Single-cell Sequencing) model. The tool processes tumor gene expression data to
predict patient responsiveness to immunotherapy.

The COMPASS model analyzes gene expression profiles to identify key immune cell
populations and pathways that contribute to treatment response prediction.
"""

import os
import sys
import pandas as pd
import asyncio
import uuid
from fastmcp import FastMCP
from typing import List, Tuple, Optional

sys.path.insert(0, f"{os.getenv('COMPASS_MODEL_PATH')}/immune-compass/COMPASS")  # noqa: E402

from compass import loadcompass  # noqa: E402

# Initialize MCP Server for COMPASS predictions
server = FastMCP("COMPASS Prediction SMCP Server")


class CompassTool:
    """
    A comprehensive tool for running immune checkpoint inhibitor (ICI) response predictions
    using the COMPASS model.

    This class provides functionality to:
    - Load pre-trained COMPASS model checkpoints
    - Process gene expression data (TPM format)
    - Predict ICI treatment response
    - Extract key immune cell populations contributing to predictions

    The COMPASS model is trained to identify immune cell concepts and pathways
    that are predictive of patient response to checkpoint inhibitor therapy.
    """

    def __init__(
        self,
        root_path: Optional[str] = None,
        ckp_path: str = "pft_leave_IMVigor210.pt",
        device: str = "cpu",
    ):
        """
        Initializes the COMPASS tool by loading the pre-trained model checkpoint.

        Args:
            root_path (str, optional): Path to the directory containing model checkpoints.
                                     If None, uses COMPASS_MODEL_PATH/immune-compass/checkpoint.
            ckp_path (str): Name of the checkpoint file to load.
                           Defaults to "pft_leave_IMVigor210.pt" (IMVigor210 cohort).
            device (str): Device for model inference ("cuda" or "cpu"). Defaults to "cuda".

        Raises:
            FileNotFoundError: If the specified checkpoint file cannot be found.
            Exception: If model loading fails due to compatibility or corruption issues.
        """
        # Construct model checkpoint path
        if root_path is None:
            compass_model_path = os.getenv("COMPASS_MODEL_PATH")
            if compass_model_path is None:
                raise ValueError("COMPASS_MODEL_PATH environment variable is not set")
            if not os.path.exists(
                os.path.join(compass_model_path, "immune-compass", "checkpoint")
            ):
                checkpoint_path = os.path.join(
                    compass_model_path, "immune-compass", "checkpoint"
                )
                raise FileNotFoundError(
                    f"COMPASS model checkpoint not found at {checkpoint_path}. Please check your COMPASS_MODEL_PATH."
                )
            root_path = os.path.join(compass_model_path, "immune-compass", "checkpoint")

        self.model_path = os.path.join(root_path, ckp_path)
        self.device = device

        # Lazy import torch for device handling
        try:
            import torch
        except ImportError:
            raise ImportError(
                "COMPASS tool requires 'torch' package. "
                "Install it with: pip install torch"
            ) from None

        # Load the pre-trained COMPASS model
        print(f"🛠️  Initializing COMPASS tool from checkpoint: {self.model_path}...")
        self.finetuner = loadcompass(
            self.model_path, weights_only=False, map_location=torch.device(self.device)
        )

        # Configure device settings for CPU inference if needed
        if self.device == "cpu":
            self.finetuner.device = "cpu"

        # Display model parameter count for transparency
        self.finetuner.count_parameters()
        print(
            "[COMPASS] Tool initialized successfully (model loaded and ready for predictions)."
        )

    def _get_top_columns_per_row(
        self,
        df: pd.DataFrame,
        top_n: int = 44,
        exclude: Optional[List[str]] = None,
    ) -> List[List[Tuple[str, float]]]:
        """
        Extracts the top-scoring immune cell concepts for each sample from COMPASS output.

        This method processes the COMPASS cell concept matrix to identify the most
        influential immune cell populations contributing to the prediction for each sample.

        Args:
            df (pd.DataFrame): DataFrame containing cell concept scores from COMPASS analysis.
                              Rows represent samples, columns represent immune cell concepts.
            top_n (int): Maximum number of top concepts to return per sample. Defaults to 44.
            exclude (List[str]): List of column names to exclude from results.
                               Defaults to ['CANCER', 'Reference'].

        Returns
            List[List[Tuple[str, float]]]: For each sample, a list of tuples containing
                                         (concept_name, concept_score) sorted by score descending.
        """
        # Set default excludes safely to avoid mutable default argument
        if exclude is None:
            exclude = ["CANCER", "Reference"]
        # Sort concepts by score (descending) for each sample
        sorted_concepts_indices = [
            row.sort_values(ascending=False).index[:top_n] for _, row in df.iterrows()
        ]

        results = []
        for i, (_, row) in enumerate(df.iterrows()):
            row_concepts = []
            for col in sorted_concepts_indices[i]:
                # Skip excluded columns (e.g., metadata columns)
                if col not in exclude:
                    row_concepts.append((col, row[col]))
            results.append(row_concepts)
        return results

    def predict(
        self,
        gene_expression_data_path: str,
        threshold: float = 0.5,
        batch_size: int = 128,
    ) -> Tuple[bool, List[Tuple[str, float]]]:
        """
        Performs immune checkpoint inhibitor response prediction on gene expression data.

        This method processes single-sample tumor gene expression data (in TPM format)
        through the COMPASS model to predict treatment response and identify key
        immune cell populations contributing to the prediction.

        Args:
            gene_expression_data_path (str): Path to the TPM expression data file.
                                                   to their expression levels in Transcripts Per Million (TPM).
            threshold (float): Prediction probability threshold for classifying samples as responders.
                             Values ≥ threshold are classified as responders. Defaults to 0.5.
            batch_size (int): Batch size for model inference. Larger values may improve speed
                            but require more memory. Defaults to 128.

        Returns
            Tuple[bool, List[Tuple[str, float]]]: A tuple containing:
                - bool: True if predicted as responder (probability ≥ threshold), False otherwise
                - List[Tuple[str, float]]: Top immune cell concepts ranked by importance,
                  where each tuple contains (concept_name, concept_score)

        Raises:
            ValueError: If gene_expression_data is empty or contains invalid values.
            RuntimeError: If model inference fails.
        """
        # Convert gene expression dictionary to DataFrame format expected by COMPASS
        df_tpm = pd.read_pickle(gene_expression_data_path)
        df_tpm.index.name = "Index"  # Required by COMPASS for gene indexing

        # Extract immune cell concepts and generate predictions using COMPASS model
        # dfct contains cell concept scores, dfpred contains response probabilities
        _, _, dfct = self.finetuner.extract(
            df_tpm, batch_size=batch_size, with_gene_level=True
        )
        _, dfpred = self.finetuner.predict(df_tpm)

        # Extract and rank the most influential immune cell concepts
        sorted_cell_concepts = self._get_top_columns_per_row(dfct)

        # Classify sample as responder based on prediction probability threshold
        # dfpred.iloc[:, 1] contains the responder probability (column 1)
        responder = dfpred.iloc[:, 1].max() >= threshold

        return responder, sorted_cell_concepts[0] if sorted_cell_concepts else []


@server.tool()
async def run_compass_prediction(
    gene_expression_data_path: str,
    threshold: float = 0.5,
    root_path: Optional[str] = None,
):
    """
    MCP Tool: Predicts immune checkpoint inhibitor (ICI) response using COMPASS model.

    This tool analyzes single-sample tumor gene expression data to predict patient
    responsiveness to immune checkpoint inhibitor therapy. The COMPASS model leverages
    immune cell concept analysis to provide both a binary prediction and interpretable
    insights into the immune microenvironment factors driving the prediction.

    Clinical Context:
    - Designed for precision oncology applications
    - Helps identify patients likely to benefit from ICI therapy
    - Provides mechanistic insights through immune cell population analysis
    - Based on validated cohorts including IMVigor210 (urothelial carcinoma)

    Args:
        gene_expression_data_path (str): Path to the TPM expression data file.
                                               Keys should be standard gene symbols (e.g., "CD274", "PDCD1", "CTLA4")
                                               Values should be normalized expression in TPM (Transcripts Per Million).
                                               Minimum ~100 genes recommended for reliable predictions.
        threshold (float): Probability threshold for responder classification (0.0-1.0).
                         Values ≥ threshold classify sample as likely responder.
                         Default 0.5 provides balanced sensitivity/specificity.
                         Consider lower thresholds (~0.3) for higher sensitivity.

    Returns
        dict: Structured prediction results containing:
            - 'prediction' (dict): Core prediction results with:
                * 'is_responder' (bool): True if predicted responder (probability ≥ threshold)
                * 'top_concepts' (list): Ranked immune cell concepts as dicts with:
                    - 'concept' (str): Name of immune cell population/concept
                    - 'score' (float): Importance score for this concept
            - 'context_info' (list): Human-readable analysis summary and status messages
            - 'error' (str, optional): Error description if prediction failed
    """
    # Generate unique request ID for tracking and logging
    request_id = str(uuid.uuid4())[:8]
    print(f"[{request_id}] Received COMPASS ICI response prediction request")

    # Initialize global COMPASS tool instance for MCP server
    # This instance will be used by the MCP tool function to serve predictions
    try:
        compass_tool = CompassTool(root_path=root_path)
        print("✅ COMPASS Prediction tool instance created and ready for MCP server")
    except Exception as e:
        print(f"❌ Error creating COMPASS Prediction tool: {str(e)}")
        print(
            "Please ensure COMPASS_MODEL_PATH is correctly set and model checkpoint exists."
        )
        raise e

    try:
        # Brief async pause to allow for proper request handling
        await asyncio.sleep(0.1)

        # Validate input parameters
        if (
            not isinstance(gene_expression_data_path, str)
            or not gene_expression_data_path
        ):
            raise ValueError(
                "Input 'gene_expression_data' must be a non-empty dictionary mapping gene symbols to TPM values."
            )

        if not (0.0 <= threshold <= 1.0):
            raise ValueError(f"Threshold must be between 0.0 and 1.0, got {threshold}")

        print(
            f"[{request_id}] Processing {len(gene_expression_data_path)} genes with threshold {threshold}"
        )

        # Execute COMPASS model prediction
        is_responder, top_concepts = compass_tool.predict(
            gene_expression_data_path, threshold=threshold
        )

        # Convert concept tuples to JSON-serializable format
        serializable_concepts = [
            {"concept": concept, "score": float(score)}
            for concept, score in top_concepts
        ]

        # Log successful completion
        response_status = "RESPONDER" if is_responder else "NON-RESPONDER"
        print(
            f"[{request_id}] ✅ COMPASS prediction completed: {response_status} ({len(serializable_concepts)} concepts)"
        )

        return {
            "prediction": {
                "is_responder": is_responder,
                "top_concepts": serializable_concepts,
            },
            "context_info": [
                "COMPASS prediction completed successfully.",
                f"Sample classified as: {'RESPONDER' if is_responder else 'NON-RESPONDER'}",
                f"Analysis based on {len(gene_expression_data_path)} input genes.",
                f"Top {len(serializable_concepts)} immune cell concepts identified.",
            ],
        }

    except (ValueError, FileNotFoundError) as e:
        error_message = f"COMPASS prediction validation error: {str(e)}"
        print(f"[{request_id}] {error_message}")
        return {
            "error": error_message,
            "context_info": ["Please check input data format and model availability."],
        }
    except Exception as e:
        error_message = f"Unexpected error during COMPASS prediction: {str(e)}"
        print(f"[{request_id}] {error_message}")
        return {
            "error": error_message,
            "context_info": ["Internal server error occurred during prediction."],
        }


if __name__ == "__main__":
    print("Starting MCP server for COMPASS Immune Response Prediction Tool...")
    print("Model: COMPASS (COMprehensive Pathway Analysis for Single-cell Sequencing)")
    print("Application: Immune Checkpoint Inhibitor Response Prediction")
    print("Server: FastMCP with streamable HTTP transport")
    print("Port: 7003 (configured to avoid conflicts with other biomedical tools)")

    # Launch the MCP server with COMPASS prediction capabilities
    server.run(
        transport="streamable-http", host="0.0.0.0", port=7003, stateless_http=True
    )
