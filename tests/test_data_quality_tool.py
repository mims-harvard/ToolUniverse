"""Tests for DataQualityTool."""

import pytest


@pytest.fixture
def tool():
    from tooluniverse.data_quality_tool import DataQualityTool

    config = {"name": "DataQuality_assess"}
    return DataQualityTool(config)


class TestDataQualityBasic:
    def test_json_array_input(self, tool):
        result = tool.run(
            {
                "data": [
                    {"a": 1, "b": "x"},
                    {"a": 2, "b": "y"},
                    {"a": 3, "b": "z"},
                ]
            }
        )
        assert result["status"] == "success"
        d = result["data"]
        assert d["overall"]["total_rows"] == 3
        assert d["overall"]["total_columns"] == 2
        assert d["overall"]["complete_cases"] == 3
        assert d["overall"]["complete_case_pct"] == 100.0

    def test_column_filter(self, tool):
        result = tool.run(
            {
                "data": [{"a": 1, "b": 2, "c": 3}],
                "columns": ["a", "c"],
            }
        )
        assert result["status"] == "success"
        cols = result["data"]["columns"]
        assert set(cols.keys()) == {"a", "c"}

    def test_missing_column_error(self, tool):
        result = tool.run(
            {
                "data": [{"a": 1}],
                "columns": ["a", "nonexistent"],
            }
        )
        assert result["status"] == "error"
        assert "nonexistent" in result["error"]

    def test_empty_data_error(self, tool):
        result = tool.run({"data": []})
        assert result["status"] == "error"

    def test_no_data_error(self, tool):
        result = tool.run({})
        assert result["status"] == "error"


class TestDataQualityMissing:
    def test_missing_values_detected(self, tool):
        result = tool.run(
            {
                "data": [
                    {"val": 1},
                    {"val": None},
                    {"val": 3},
                ]
            }
        )
        d = result["data"]
        assert d["columns"]["val"]["missing_count"] == 1
        assert d["columns"]["val"]["missing_pct"] == pytest.approx(33.33, abs=0.1)

    def test_high_missing_warning(self, tool):
        # >20% missing should trigger warning
        data = [{"v": None}] * 3 + [{"v": 1}] * 7
        result = tool.run({"data": data})
        warnings = result["data"]["warnings"]
        high_missing = [w for w in warnings if w["type"] == "high_missing"]
        assert len(high_missing) == 1
        assert high_missing[0]["column"] == "v"


class TestDataQualityNumeric:
    def test_numeric_stats(self, tool):
        result = tool.run({"data": [{"x": 10}, {"x": 20}, {"x": 30}]})
        col = result["data"]["columns"]["x"]
        assert col["min"] == 10.0
        assert col["max"] == 30.0
        assert col["mean"] == 20.0
        assert col["unique_values"] == 3

    def test_zero_variance_warning(self, tool):
        result = tool.run(
            {"data": [{"c": 5}, {"c": 5}, {"c": 5}]}
        )
        warnings = result["data"]["warnings"]
        zv = [w for w in warnings if w["type"] == "zero_variance"]
        assert len(zv) == 1
        assert zv[0]["column"] == "c"


class TestDataQualityCorrelation:
    def test_high_correlation_warning(self, tool):
        result = tool.run(
            {
                "data": [
                    {"x": 1, "y": 2},
                    {"x": 2, "y": 4},
                    {"x": 3, "y": 6},
                    {"x": 4, "y": 8},
                ]
            }
        )
        warnings = result["data"]["warnings"]
        hc = [w for w in warnings if w["type"] == "high_correlation"]
        assert len(hc) == 1
        assert "1.0" in hc[0]["detail"]

    def test_no_correlation_warning_for_uncorrelated(self, tool):
        result = tool.run(
            {
                "data": [
                    {"a": 1, "b": 10},
                    {"a": 2, "b": 5},
                    {"a": 3, "b": 15},
                    {"a": 4, "b": 2},
                ]
            }
        )
        warnings = result["data"]["warnings"]
        hc = [w for w in warnings if w["type"] == "high_correlation"]
        assert len(hc) == 0


class TestDataQualityCategorical:
    def test_categorical_stats(self, tool):
        result = tool.run(
            {
                "data": [
                    {"color": "red"},
                    {"color": "blue"},
                    {"color": "red"},
                    {"color": "red"},
                ]
            }
        )
        col = result["data"]["columns"]["color"]
        assert col["mode"] == "red"
        assert col["top_values"]["red"] == 3
        assert col["top_values"]["blue"] == 1


class TestDataQualityOutliers:
    def test_outlier_detection(self, tool):
        # Create data with clear outlier
        data = [{"v": float(i)} for i in range(100)]
        data.append({"v": 1000.0})  # clear outlier
        result = tool.run({"data": data})
        warnings = result["data"]["warnings"]
        outliers = [w for w in warnings if w["type"] == "potential_outliers"]
        assert len(outliers) == 1
        assert "1000.0" in outliers[0]["detail"]
