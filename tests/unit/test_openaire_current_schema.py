from tooluniverse.openaire_tool import OpenAIRETool


def _tool():
    return OpenAIRETool({"name": "OpenAIRE_search_publications"})


def test_normalize_current_entity_schema_and_singleton_shapes():
    payload = {
        "response": {
            "results": {
                "result": {
                    "metadata": {
                        "oaf:entity": {
                            "oaf:result": {
                                "title": [
                                    {"$": "Primary title"},
                                    {"$": "normalized title"},
                                ],
                                "creator": {"$": "Dmitriy Sonkin"},
                                "dateofacceptance": {"$": "2015-10-22"},
                                "pid": {
                                    "@classid": "doi",
                                    "$": "10.7554/elife.10279",
                                },
                                "children": {
                                    "instance": {
                                        "webresource": {
                                            "url": {
                                                "$": "https://example.org/a&amp;b"
                                            }
                                        }
                                    }
                                },
                            }
                        }
                    }
                }
            }
        }
    }

    result = _tool()._normalize(payload, "publications")

    assert result == [
        {
            "title": "Primary title",
            "authors": ["Dmitriy Sonkin"],
            "year": 2015,
            "doi": "10.7554/elife.10279",
            "url": "https://example.org/a&b",
            "type": "publications",
            "source": "OpenAIRE",
        }
    ]


def test_normalize_lists_and_falls_back_to_doi_url():
    payload = {
        "response": {
            "results": {
                "result": [
                    {
                        "metadata": {
                            "oaf:entity": {
                                "oaf:result": {
                                    "title": {"$": "CRISPR paper"},
                                    "creator": [
                                        {"$": "Author One"},
                                        {"$": "Author Two"},
                                    ],
                                    "dateofacceptance": {"$": "2020"},
                                    "pid": [
                                        {"@classid": "pmid", "$": 123},
                                        {
                                            "@classid": "doi",
                                            "$": "10.1000/test",
                                        },
                                    ],
                                }
                            }
                        }
                    }
                ]
            }
        }
    }

    result = _tool()._normalize(payload, "publications")[0]

    assert result["title"] == "CRISPR paper"
    assert result["authors"] == ["Author One", "Author Two"]
    assert result["year"] == 2020
    assert result["doi"] == "10.1000/test"
    assert result["url"] == "https://doi.org/10.1000/test"


def test_normalize_retains_legacy_direct_oaf_result_shape():
    payload = {
        "response": {
            "results": {
                "result": [
                    {
                        "metadata": {
                            "oaf:result": {
                                "title": {"$": "Legacy title"},
                            }
                        }
                    }
                ]
            }
        }
    }

    result = _tool()._normalize(payload, "datasets")[0]

    assert result["title"] == "Legacy title"
    assert result["type"] == "datasets"
