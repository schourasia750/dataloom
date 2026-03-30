"""Dataset quality analysis and remediation helpers."""

from __future__ import annotations

import math
import re
from typing import Any

import pandas as pd

from app.services.transformation_service import TransformationError

PATTERN_DETECTORS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"),
    "phone": re.compile(r"^\+?[0-9()\-\s]{7,}$"),
    "zip": re.compile(r"^\d{5}(?:-\d{4})?$"),
    "numeric_id": re.compile(r"^\d+$"),
    "code": re.compile(r"^[A-Z]{2,}(?:[-_][A-Z0-9]+|[A-Z0-9]+)*$"),
    "iso_date": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
}

QUALITY_SCAN_OPERATION = "qualityAssessment"
QUALITY_FIX_OPERATION = "qualityFix"


def _clean_scalar(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _dominant_pattern(values: list[str]) -> tuple[str | None, list[str]]:
    if len(values) < 5:
        return None, []

    best_name = None
    best_matches: list[str] = []
    for name, pattern in PATTERN_DETECTORS.items():
        matches = [value for value in values if pattern.fullmatch(value)]
        if len(matches) > len(best_matches):
            best_name = name
            best_matches = matches

    if not best_name:
        return None, []

    coverage = len(best_matches) / len(values)
    if coverage < 0.7:
        return None, []

    return best_name, best_matches


def analyze_quality(df: pd.DataFrame) -> dict[str, Any]:
    """Inspect a dataset for duplicates, outliers, and pattern violations."""
    duplicate_mask = df.duplicated(keep=False)
    duplicate_rows = [int(index) for index in df.index[duplicate_mask].tolist()]

    duplicate_issue: dict[str, Any] = {
        "type": "duplicates",
        "label": "Duplicate rows",
        "count": len(duplicate_rows),
        "row_indices": duplicate_rows,
        "fix_label": "Remove duplicates",
        "fix_action": {
            "issue_type": "duplicates",
            "columns": df.columns.tolist(),
            "keep": "first",
        },
    }

    outlier_issues: list[dict[str, Any]] = []
    total_outliers = 0
    numeric_df = df.select_dtypes(include="number")
    for column in numeric_df.columns:
        series = pd.to_numeric(numeric_df[column], errors="coerce").dropna()
        if len(series) < 4:
            continue
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        if pd.isna(iqr) or iqr == 0:
            continue
        lower_bound = float(q1 - 1.5 * iqr)
        upper_bound = float(q3 + 1.5 * iqr)
        mask = pd.to_numeric(df[column], errors="coerce").between(lower_bound, upper_bound, inclusive="both")
        row_indices = [int(index) for index in df.index[~mask.fillna(False)].tolist()]
        if not row_indices:
            continue
        total_outliers += len(row_indices)
        outlier_issues.append(
            {
                "type": "outliers",
                "label": f"Outliers in {column}",
                "column": column,
                "count": len(row_indices),
                "row_indices": row_indices,
                "details": {
                    "lower_bound": round(lower_bound, 4),
                    "upper_bound": round(upper_bound, 4),
                },
                "fix_label": "Cap outliers",
                "fix_action": {
                    "issue_type": "outliers",
                    "column": column,
                    "strategy": "cap",
                },
            }
        )

    pattern_issues: list[dict[str, Any]] = []
    total_pattern_violations = 0
    for column in df.columns:
        series = df[column]
        if not (pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series)):
            continue
        trimmed = series.map(lambda value: value.strip() if isinstance(value, str) else value)
        values = [value for value in trimmed.tolist() if isinstance(value, str) and value]
        pattern_name, _ = _dominant_pattern(values)
        if not pattern_name:
            continue
        detector = PATTERN_DETECTORS[pattern_name]
        row_indices = [
            int(index)
            for index, value in trimmed.items()
            if isinstance(value, str) and value and not detector.fullmatch(value)
        ]
        if not row_indices:
            continue
        total_pattern_violations += len(row_indices)
        pattern_issues.append(
            {
                "type": "patternViolations",
                "label": f"{column} breaks the dominant {pattern_name} pattern",
                "column": column,
                "pattern_name": pattern_name,
                "count": len(row_indices),
                "row_indices": row_indices,
                "fix_label": "Blank invalid values",
                "fix_action": {
                    "issue_type": "patternViolations",
                    "column": column,
                    "pattern_name": pattern_name,
                    "strategy": "blank_invalid",
                },
            }
        )

    total_cells = max(len(df.index) * max(len(df.columns), 1), 1)
    weighted_penalty = (
        len(duplicate_rows) * 1.5 + total_outliers * 1.0 + total_pattern_violations * 1.2
    ) / total_cells
    score = max(0, min(100, round(100 - weighted_penalty * 100)))

    return {
        "score": score,
        "summary": {
            "duplicate_rows": len(duplicate_rows),
            "outliers": total_outliers,
            "pattern_violations": total_pattern_violations,
            "total_issues": len(duplicate_rows) + total_outliers + total_pattern_violations,
        },
        "issues": {
            "duplicates": duplicate_issue,
            "outliers": outlier_issues,
            "pattern_violations": pattern_issues,
        },
    }


def apply_quality_fix(df: pd.DataFrame, issue_type: str, **kwargs: Any) -> pd.DataFrame:
    """Apply an automated remediation for a detected quality issue."""
    if issue_type == "duplicates":
        columns = kwargs.get("columns") or df.columns.tolist()
        keep = kwargs.get("keep", "first")
        missing = [column for column in columns if column not in df.columns]
        if missing:
            raise TransformationError(f"Columns {missing} not found in dataset")
        return df.drop_duplicates(subset=columns, keep=keep).reset_index(drop=True)

    if issue_type == "outliers":
        column = kwargs.get("column")
        if column not in df.columns:
            raise TransformationError(f"Column '{column}' not found")
        series = pd.to_numeric(df[column], errors="coerce")
        clean = series.dropna()
        if len(clean) < 4:
            raise TransformationError(f"Not enough numeric values in '{column}' to fix outliers")
        q1 = clean.quantile(0.25)
        q3 = clean.quantile(0.75)
        iqr = q3 - q1
        if pd.isna(iqr) or iqr == 0:
            raise TransformationError(f"Unable to determine outlier bounds for '{column}'")
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        fixed = df.copy()
        fixed[column] = series.clip(lower=lower_bound, upper=upper_bound)
        return fixed

    if issue_type == "patternViolations":
        column = kwargs.get("column")
        pattern_name = kwargs.get("pattern_name")
        if column not in df.columns:
            raise TransformationError(f"Column '{column}' not found")
        if pattern_name not in PATTERN_DETECTORS:
            raise TransformationError(f"Unsupported pattern '{pattern_name}'")
        detector = PATTERN_DETECTORS[pattern_name]
        fixed = df.copy()

        def _sanitize(value: Any) -> Any:
            if not isinstance(value, str):
                return value
            trimmed = value.strip()
            if not trimmed:
                return value
            return trimmed if detector.fullmatch(trimmed) else ""

        fixed[column] = fixed[column].map(_sanitize)
        return fixed

    raise TransformationError(f"Unsupported quality fix type: {issue_type}")
