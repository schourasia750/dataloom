"""Tests for automatic dataset profiling helpers."""

import pandas as pd

from app.utils.pandas_helpers import dataframe_to_response


def test_dataframe_response_includes_profile_summary_and_column_stats():
    df = pd.DataFrame(
        {
            "name": ["Alice", "Bob", "Alice", None],
            "score": [10, 20, None, 40],
        }
    )

    response = dataframe_to_response(df)

    assert response["profile"]["summary"] == {
        "row_count": 4,
        "column_count": 2,
        "missing_cells": 2,
        "duplicate_rows": 0,
    }

    name_profile = next(column for column in response["profile"]["columns"] if column["name"] == "name")
    assert name_profile["data_type"] == "str"
    assert name_profile["missing_count"] == 1
    assert name_profile["unique_count"] == 2
    assert name_profile["sample_values"] == ["Alice", "Bob"]

    score_profile = next(column for column in response["profile"]["columns"] if column["name"] == "score")
    assert score_profile["data_type"] == "float"
    assert score_profile["missing_count"] == 1
    assert score_profile["mean"] == 23.33
    assert score_profile["min"] == 10.0
    assert score_profile["max"] == 40.0
