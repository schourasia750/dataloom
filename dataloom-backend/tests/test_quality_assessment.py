"""Tests for automated data quality assessment and one-click fixes."""

import pandas as pd

from app.services.quality_service import analyze_quality, apply_quality_fix


def test_analyze_quality_detects_duplicates_outliers_and_pattern_violations():
    df = pd.DataFrame(
        {
            "email": [
                "alice@example.com",
                "alice@example.com",
                "bob@example.com",
                "invalid-email",
                "carol@example.com",
                "dave@example.com",
            ],
            "amount": [10, 10, 12, 13, 15, 500],
            "region": ["NORTH", "NORTH", "SOUTH", "WEST", "EAST", "NORTH"],
        }
    )

    result = analyze_quality(df)

    assert result["score"] < 100
    assert result["issues"]["duplicates"]["count"] == 2
    assert result["summary"]["outliers"] == 1
    assert result["summary"]["pattern_violations"] == 1
    assert result["issues"]["outliers"][0]["column"] == "amount"
    assert result["issues"]["pattern_violations"][0]["column"] == "email"


def test_apply_quality_fix_duplicates_removes_exact_matches():
    df = pd.DataFrame({"name": ["Alice", "Alice", "Bob"], "age": [30, 30, 40]})

    result = apply_quality_fix(df, "duplicates", columns=["name", "age"], keep="first")

    assert len(result) == 2


def test_apply_quality_fix_outliers_caps_values():
    df = pd.DataFrame({"amount": [10, 11, 12, 13, 400]})

    result = apply_quality_fix(df, "outliers", column="amount")

    assert result["amount"].max() < 400


def test_apply_quality_fix_pattern_violations_blanks_invalid_values():
    df = pd.DataFrame({"email": ["alice@example.com", "not-an-email", " bob@example.com "]})

    result = apply_quality_fix(df, "patternViolations", column="email", pattern_name="email")

    assert result["email"].tolist() == ["alice@example.com", "", "bob@example.com"]
