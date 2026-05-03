import pytest
from unittest.mock import MagicMock, patch
from tooluniverse.fda_pharmacogenomic_biomarkers_tool import FDAPharmacogenomicBiomarkersTool

# Sample HTML Content mimicking the structure of the FDA page
SAMPLE_HTML = """
<html>
<body>
    <div role="main">
        <table>
            <thead>
                <tr>
                    <th scope="col">Drug</th>
                    <th scope="col">Therapeutic Area</th>
                    <th scope="col">Biomarker</th>
                    <th scope="col">Labeling Section</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Abacavir</td>
                    <td>Antivirals</td>
                    <td>HLA-B*5701</td>
                    <td>Boxed Warning, Warnings and Precautions, Indications and Usage</td>
                </tr>
                <tr>
                    <td>Warfarin</td>
                    <td>Hematology</td>
                    <td>CYP2C9, VKORC1</td>
                    <td>Dosage and Administration, Clinical Pharmacology</td>
                </tr>
                <tr>
                    <td>Codeine</td>
                    <td>Anesthesiology</td>
                    <td>CYP2D6</td>
                    <td>Boxed Warning, Warnings and Precautions, Drug Interactions, Use in Specific Populations, Clinical Pharmacology</td>
                </tr>
            </tbody>
        </table>
    </div>
</body>
</html>
"""

@pytest.fixture
def fda_tool():
    config = {
        "name": "fda_pharmacogenomic_biomarkers",
        "type": "FDAPharmacogenomicBiomarkersTool"
    }
    return FDAPharmacogenomicBiomarkersTool(config)

def test_parse_html_table(fda_tool):
    records = fda_tool._parse_html_table(SAMPLE_HTML)
    assert len(records) == 3
    assert records[0]["Drug"] == "Abacavir"
    assert records[0]["Biomarker"] == "HLA-B*5701"
    assert records[1]["Drug"] == "Warfarin"
    assert records[2]["Biomarker"] == "CYP2D6"

@patch("requests.get")
def test_run_with_mock_data(mock_get, fda_tool):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = SAMPLE_HTML
    mock_get.return_value = mock_response

    # Test filtering by drug name
    result_drug = fda_tool.run({"drug_name": "Warfarin"})
    assert result_drug["count"] == 1
    assert result_drug["results"][0]["Drug"] == "Warfarin"
    
    # Test filtering by biomarker
    result_bio = fda_tool.run({"biomarker": "HLA-B"})
    assert result_bio["count"] == 1
    assert result_bio["results"][0]["Drug"] == "Abacavir"

    # Test no filter
    result_all = fda_tool.run({})
    assert result_all["count"] == 3
    
    # Verify User-Agent header was called
    args, kwargs = mock_get.call_args
    assert "User-Agent" in kwargs["headers"]

@patch("requests.get")
def test_run_network_error(mock_get, fda_tool):
    # Setup mock to raise exception
    mock_get.side_effect = Exception("Network Error")
    
    result = fda_tool.run({})
    assert "error" in result
    assert "Network Error" in result["error"]
