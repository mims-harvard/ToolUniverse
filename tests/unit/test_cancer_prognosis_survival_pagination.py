from unittest.mock import Mock

from tooluniverse.cancer_prognosis_tool import CancerPrognosisTool


def _tool():
    return CancerPrognosisTool(
        {
            "parameter": {
                "properties": {
                    "operation": {"type": "string", "enum": ["get_survival_data"]}
                }
            }
        }
    )


def test_api_get_all_pages_advances_page_number():
    tool = _tool()
    tool._api_get = Mock(side_effect=[[1, 2], [3]])

    records, pages = tool._api_get_all_pages("/items", page_size=2)

    assert records == [1, 2, 3]
    assert pages == 2
    assert tool._api_get.call_args_list[0].kwargs["params"]["pageNumber"] == 0
    assert tool._api_get.call_args_list[1].kwargs["params"]["pageNumber"] == 1


def test_survival_patient_arrays_have_continuation():
    tool = _tool()
    clinical = []
    for i in range(5):
        patient = f"P{i}"
        clinical.extend(
            [
                {
                    "patientId": patient,
                    "clinicalAttributeId": "OS_MONTHS",
                    "value": str(i + 1),
                },
                {
                    "patientId": patient,
                    "clinicalAttributeId": "OS_STATUS",
                    "value": "1:DECEASED",
                },
                {
                    "patientId": patient,
                    "clinicalAttributeId": "DFS_MONTHS",
                    "value": str(i + 2),
                },
                {
                    "patientId": patient,
                    "clinicalAttributeId": "DFS_STATUS",
                    "value": "0:DiseaseFree",
                },
            ]
        )
    tool._api_get_all_pages = Mock(return_value=(clinical, 3))

    data = tool.run({"cancer": "BRCA", "max_patients": 2, "patient_offset": 2})["data"]

    assert data["clinical_records_fetched"] == 20
    assert data["clinical_pages_fetched"] == 3
    assert [p["patient_id"] for p in data["overall_survival"]["patients"]] == [
        "P2",
        "P3",
    ]
    assert data["overall_survival"]["has_more"] is True
    assert data["overall_survival"]["next_patient_offset"] == 4
    assert data["disease_free_survival"]["next_patient_offset"] == 4
