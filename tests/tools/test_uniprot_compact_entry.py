from unittest.mock import Mock, patch

from tooluniverse.uniprot_tool import UniProtRESTTool


def _tool():
    return UniProtRESTTool(
        {
            "parameter": {
                "properties": {
                    "compact": {
                        "default": True,
                    }
                }
            },
            "fields": {
                "endpoint": "https://rest.uniprot.org/uniprotkb/{accession}.json",
            }
        }
    )


def _response(payload):
    response = Mock()
    response.status_code = 200
    response.json.return_value = payload
    return response


def test_compact_entry_returns_bounded_summary():
    payload = {
        "entryType": "UniProtKB reviewed (Swiss-Prot)",
        "primaryAccession": "P05067",
        "uniProtkbId": "A4_HUMAN",
        "proteinDescription": {
            "recommendedName": {"fullName": {"value": "Amyloid-beta precursor protein"}}
        },
        "genes": [{"geneName": {"value": "APP"}}],
        "organism": {"scientificName": "Homo sapiens", "taxonId": 9606},
        "sequence": {"value": "M" * 20, "length": 20},
        "comments": [
            {"commentType": "FUNCTION", "texts": [{"value": "Function text"}]},
            {"commentType": "DISEASE", "texts": [{"value": "Disease text"}]},
        ],
        "features": [
            {"type": "Chain", "description": "Processed chain"} for _ in range(105)
        ],
        "uniProtKBCrossReferences": [{"database": "PDB"} for _ in range(10)],
    }

    with patch(
        "tooluniverse.uniprot_tool.requests.get", return_value=_response(payload)
    ):
        result = _tool().run({"accession": "P05067", "compact": True})

    assert result["status"] == "success"
    assert result["data"]["primaryAccession"] == "P05067"
    assert result["data"]["protein_name"] == "Amyloid-beta precursor protein"
    assert result["data"]["gene_names"] == ["APP"]
    assert len(result["data"]["features"]) == 100
    assert result["data"]["xref_count"] == 10
    assert result["metadata"]["compact"] is True
    assert result["metadata"]["total_features"] == 105


def test_compact_entry_is_default_behavior():
    payload = {
        "primaryAccession": "P05067",
        "proteinDescription": {
            "recommendedName": {"fullName": {"value": "Amyloid-beta precursor protein"}}
        },
    }

    with patch(
        "tooluniverse.uniprot_tool.requests.get", return_value=_response(payload)
    ):
        result = _tool().run({"accession": "P05067"})

    assert result["status"] == "success"
    assert result["metadata"]["compact"] is True
    assert result["data"]["primaryAccession"] == "P05067"


def test_full_entry_remains_available_with_compact_false():
    payload = {"primaryAccession": "P05067", "large": {"nested": True}}

    with patch(
        "tooluniverse.uniprot_tool.requests.get", return_value=_response(payload)
    ):
        result = _tool().run({"accession": "P05067", "compact": False})

    assert result == payload
