import numpy
from .base_tool import BaseTool
from .tool_registry import register_tool
import warnings

# Patch for numpy.VisibleDeprecationWarning for newer numpy versions
if not hasattr(numpy, "VisibleDeprecationWarning"):
    import numpy.exceptions

    numpy.VisibleDeprecationWarning = numpy.exceptions.VisibleDeprecationWarning


def _patch_torch_load():
    """Lazy patch for torch.load to set weights_only=False by default."""
    try:
        import torch

        if not hasattr(torch.load, "_patched_by_tooluniverse"):
            _original_torch_load = torch.load

            def _patched_torch_load(*args, **kwargs):
                if "weights_only" not in kwargs:
                    kwargs["weights_only"] = False
                return _original_torch_load(*args, **kwargs)

            torch.load = _patched_torch_load
            torch.load._patched_by_tooluniverse = True
    except ImportError:
        # torch is not installed, skip patching
        pass


# Lazy import ADMETModel with error handling
def _import_admet_model():
    """Lazy import ADMETModel with proper error handling."""
    try:
        # Patch torch.load before importing admet_ai
        _patch_torch_load()

        # Suppress admet-ai specific warnings during import
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", category=DeprecationWarning, module="pkg_resources"
            )
            warnings.filterwarnings(
                "ignore", category=DeprecationWarning, module="admet_ai"
            )
            from admet_ai import ADMETModel  # noqa: E402

        return ADMETModel
    except ImportError as e:
        raise ImportError(
            "ADMETModel requires 'admet-ai' package. "
            "Install it with: pip install tooluniverse[ml]"
        ) from e


@register_tool("ADMETAITool")
class ADMETAITool(BaseTool):
    """Tool to predict ADMET properties for a given SMILES string using the admet-ai Python package."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model = None
        self._dependencies_available = False
        self._dependency_error = None

        # Lazy import ADMETModel to avoid requiring torch at module import time
        try:
            ADMETModel = _import_admet_model()
            # Initialize the model once during tool initialization
            self.model = ADMETModel()
            self._dependencies_available = True
        except ImportError as e:
            self._dependency_error = e
            # Don't raise - allow tool to be created but mark as unavailable
            import warnings

            warnings.warn(
                "ADMETAITool initialized without dependencies. "
                "Install missing packages with: pip install tooluniverse[ml]",
                UserWarning,
                stacklevel=2,
            )

    def _predict(self, smiles: str) -> dict:
        """
        Gets ADMET predictions for the given smiles
        """
        if not self._dependencies_available:
            raise ImportError(
                "ADMETModel requires 'admet-ai' package. "
                "Install it with: pip install tooluniverse[ml]"
            ) from self._dependency_error

        # Reuse the pre-loaded model instead of creating a new one
        preds = self.model.predict(smiles=smiles)
        return preds

    def run(self, arguments: dict) -> dict:
        """
        Predicts ADMET properties for a given SMILES string.

        Args:
            smiles: The SMILES string(s) of the molecule(s).

        Returns
            A dictionary mapping each SMILES string to a subdictionary of
            selected ADMET properties and their predicted values.
        """
        smiles = arguments.get("smiles", [])
        # Accept single SMILES string, coerce to list
        if isinstance(smiles, str):
            smiles = [smiles]
        if not smiles:
            return {"status": "error", "error": "SMILES string cannot be empty."}

        # Get the columns to select from the tool definition
        columns = getattr(self, "columns", None)
        if columns is None and hasattr(self, "tool_config") and self.tool_config:
            columns = self.tool_config.get("columns", None)

        try:
            predictions = self._predict(smiles)
            if (hasattr(predictions, "empty") and predictions.empty) or (
                not hasattr(predictions, "empty") and not predictions
            ):
                return {
                    "status": "error",
                    "error": "No predictions could be extracted.",
                }

            # Expand columns to include _drugbank_approved_percentile columns
            # if present
            if columns is not None:
                expanded_columns = []
                for col in columns:
                    expanded_columns.append(col)
                    percentile_col = f"{col}_drugbank_approved_percentile"
                    if percentile_col in predictions.columns:
                        expanded_columns.append(percentile_col)
                predictions = predictions[expanded_columns]

            # Organize output: {smiles: {col: value, ...}, ...}
            result = {}
            for idx, row in predictions.iterrows():
                result[idx] = {col: row[col] for col in predictions.columns}
            return result
        except Exception as e:
            return {"status": "error", "error": f"An unexpected error occurred: {e}"}
